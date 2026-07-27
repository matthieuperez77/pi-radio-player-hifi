"""Pilotage audio via mpv en mode démon, contrôlé par son socket IPC JSON.

Choix : piloter le binaire `mpv` par son socket plutôt que d'utiliser la
lib python-mpv (binding libmpv) - une seule dépendance système (`mpv`),
pas de lib C supplémentaire à installer.
"""

import json
import logging
import socket
import subprocess
import threading
import time

from gpiozero import OutputDevice

from radio.config import AUDIO_DEVICE, HAT_MUTE_ACTIVE_HIGH, HAT_MUTE_PIN, ROOT

log = logging.getLogger(__name__)

SOCKET_PATH = ROOT / "var" / "mpv.sock"


class Player:
    def __init__(self):
        SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        args = [
            "mpv",
            "--idle",
            "--no-video",
            "--no-terminal",
            f"--input-ipc-server={SOCKET_PATH}",
        ]
        if AUDIO_DEVICE:
            # Cible explicitement le HAT InnoMaker DAC Mini (PCM5122) quand
            # ce n'est pas la carte ALSA par défaut du système (cf. `aplay -l`).
            args.append(f"--audio-device={AUDIO_DEVICE}")
        self._proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._wait_for_socket()
        self.on_error = None  # callback(message: str), assigné par l'appelant
        self._closed = False
        self._event_thread = threading.Thread(target=self._listen_events, daemon=True)
        self._event_thread.start()

    def _wait_for_socket(self, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if SOCKET_PATH.exists():
                return
            time.sleep(0.1)
        raise RuntimeError("mpv n'a pas créé son socket IPC à temps")

    def _listen_events(self):
        """Connexion IPC dédiée à l'écoute (en plus des connexions ponctuelles
        de _command) : mpv diffuse ses évènements à tout client connecté sans
        rien demander explicitement. Sert à détecter un flux injoignable."""
        while not self._closed:
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.connect(str(SOCKET_PATH))
                    buf = b""
                    while not self._closed:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            self._handle_event(line)
            except OSError:
                if not self._closed:
                    time.sleep(1)  # mpv pas encore prêt / socket recréé, on retente

    def _handle_event(self, line: bytes):
        try:
            msg = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if msg.get("event") == "end-file" and msg.get("reason") == "error" and self.on_error:
            self.on_error(msg.get("file_error") or "flux injoignable")

    def _command(self, *args):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(SOCKET_PATH))
            sock.sendall((json.dumps({"command": list(args)}) + "\n").encode())
            return sock.recv(4096)

    def play(self, stream_url: str, needs_ytdl: bool = False):
        if needs_ytdl:
            self._command("set_property", "ytdl", True)
        self._command("loadfile", stream_url, "replace")

    def set_volume(self, percent: int):
        self._command("set_property", "volume", max(0, min(100, percent)))

    def stop(self):
        self._command("stop")

    def close(self):
        self._closed = True
        try:
            self._command("quit")
        except OSError:
            pass
        self._proc.wait(timeout=5)


class HatMute:
    """Pilote le pin de mute matériel du HAT InnoMaker DAC Mini (GPIO6) :
    une entrée côté HAT qui coupe le son au niveau du DAC, indépendamment
    du volume logiciel mpv. Polarité (HAT_MUTE_ACTIVE_HIGH) non documentée
    précisément par le constructeur - à confirmer une fois le HAT branché
    (cf. README) ; sans conséquence tant que rien n'est câblé sur ce GPIO."""

    def __init__(self):
        self._output = OutputDevice(HAT_MUTE_PIN, active_high=HAT_MUTE_ACTIVE_HIGH, initial_value=False)

    def set_muted(self, muted: bool):
        self._output.value = muted

    def close(self):
        self._output.close()
