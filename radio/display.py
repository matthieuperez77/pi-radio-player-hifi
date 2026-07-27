"""Pilotage de l'écran LCD caractères (I2C, backpack PCF8574 type Qapass) et
composition des différents écrans.

Sans la lib RPLCD installée (ou le bus I2C inaccessible), tourne en mode
simulation : écrit l'état des lignes dans var/preview/lcd.txt plutôt que de
planter - pratique pour développer/tester le contenu des écrans sans le
matériel branché, dans le même esprit que le SimulatedEPD de l'ancien projet.
"""

import logging
import threading
import unicodedata

from radio.config import LCD_COLS, LCD_I2C_ADDRESS, LCD_ROWS, I2C_BUS, ROOT

log = logging.getLogger(__name__)

PREVIEW_FILE = ROOT / "var" / "preview" / "lcd.txt"

SCROLL_INTERVAL_SECONDS = 0.4
SCROLL_GAP = "   "  # séparateur entre la fin et la reprise du défilement en boucle
ERROR_CYCLE_SECONDS = 3.0
BACKLIGHT_GRACE_SECONDS = 4.0  # délai avant extinction si "LCD éteint pendant l'écoute"

_LIGATURES = {"œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE"}
_PUNCTUATION = {
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "«": '"', "»": '"', "–": "-", "—": "-",
}


def _strip_accents(text: str) -> str:
    """Translittère en ASCII pur (é->e, ç->c, œ->oe...).

    La ROM du contrôleur HD44780 réellement câblé ne correspond ni à la
    table A02 (RPLCD, par défaut) ni à la table A00 : les caractères
    accentués s'affichent comme des glyphes erronés dans les deux cas
    (constaté au test le 2026-07-27). On évite donc d'envoyer au LCD tout
    caractère hors ASCII plutôt que de dépendre d'une table qui ne
    correspond pas au matériel.
    """
    for src, dst in {**_LIGATURES, **_PUNCTUATION}.items():
        text = text.replace(src, dst)
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.encode("ascii", "replace").decode("ascii")


def _pad(text: str, width: int = LCD_COLS) -> str:
    return _strip_accents(text)[:width].ljust(width)


class SimulatedLCD:
    def __init__(self):
        PREVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._backlight_enabled = True
        self._lines = [""] * LCD_ROWS
        log.warning("RPLCD/I2C indisponible -> LCD simulé, rendu écrit dans %s", PREVIEW_FILE)

    @property
    def backlight_enabled(self):
        return self._backlight_enabled

    @backlight_enabled.setter
    def backlight_enabled(self, value: bool):
        self._backlight_enabled = value
        self._flush()

    def clear(self):
        self._lines = [""] * LCD_ROWS
        self._flush()

    def write_row(self, row: int, text: str):
        self._lines[row] = text
        self._flush()

    def _flush(self):
        backlight = "ON" if self.backlight_enabled else "OFF"
        content = f"backlight: {backlight}\n" + "\n".join(f"[{line}]" for line in self._lines)
        PREVIEW_FILE.write_text(content + "\n", encoding="utf-8")

    def close(self):
        pass


class RPLCDDisplay:
    def __init__(self):
        from RPLCD.i2c import CharLCD

        self._lcd = CharLCD(
            i2c_expander="PCF8574",
            address=LCD_I2C_ADDRESS,
            port=I2C_BUS,
            cols=LCD_COLS,
            rows=LCD_ROWS,
            auto_linebreaks=False,
        )

    @property
    def backlight_enabled(self):
        return self._lcd.backlight_enabled

    @backlight_enabled.setter
    def backlight_enabled(self, value: bool):
        self._lcd.backlight_enabled = value

    def clear(self):
        self._lcd.clear()

    def write_row(self, row: int, text: str):
        self._lcd.cursor_pos = (row, 0)
        self._lcd.write_string(text)

    def close(self):
        self._lcd.close(clear=True)


def _load_driver():
    try:
        return RPLCDDisplay()
    except (ImportError, OSError) as exc:
        log.warning("Impossible d'initialiser le LCD réel (%s) -> simulation", exc)
        return SimulatedLCD()


class Display:
    def __init__(self):
        self.lcd = _load_driver()
        self.follow_playback = True  # écrasé juste après construction par l'état persisté (cf. main.py)
        self._ticker_stop = None
        self._ticker_thread = None
        self._grace_timer = None

    # -- rétroéclairage / mode "LCD éteint pendant l'écoute" -----------------

    def set_follow_playback(self, follow: bool):
        self.follow_playback = follow

    def set_backlight(self, on: bool):
        self.lcd.backlight_enabled = on

    def _cancel_pending(self):
        if self._grace_timer:
            self._grace_timer.cancel()
            self._grace_timer = None
        self._stop_ticker()

    # -- écrans ---------------------------------------------------------------

    def show_boot(self):
        self._cancel_pending()
        self._render_static(["Démarrage...", ""])
        self.set_backlight(True)

    def show_station(self, station: dict):
        """Nom de station affiché immédiatement à la sélection - toujours
        rendu, rétroéclairage réveillé, indépendamment du réglage
        "LCD éteint pendant l'écoute". Si ce réglage est actif, le
        rétroéclairage s'éteindra tout seul après un court délai de grâce."""
        self._cancel_pending()
        self._render_static([station["name"], ""])
        self.set_backlight(True)
        if not self.follow_playback:
            self._grace_timer = threading.Timer(BACKLIGHT_GRACE_SECONDS, lambda: self.set_backlight(False))
            self._grace_timer.daemon = True
            self._grace_timer.start()

    def show_now_playing(self, station: dict, emission_text: str | None):
        """Appelé au refresh métadonnées périodique. N'a d'effet que si le
        réglage "LCD actif pendant l'écoute" est activé - sinon le
        rétroéclairage reste éteint (déjà coupé par show_station)."""
        if not self.follow_playback:
            return
        self._cancel_pending()
        self.set_backlight(True)
        self.lcd.write_row(0, _pad(station["name"]))
        if LCD_ROWS < 2:
            return
        if not emission_text:
            self.lcd.write_row(1, _pad(""))
        elif len(emission_text) <= LCD_COLS:
            self.lcd.write_row(1, _pad(emission_text))
        else:
            self._start_scroll(1, emission_text)

    def show_error(self, station_name: str, message: str, ip: str | None, username: str):
        self._cancel_pending()
        self.set_backlight(True)
        screen_a = [station_name, message]
        screen_b = [f"IP {ip}" if ip else "IP indisponible", f"user {username}"]
        if LCD_ROWS >= 4:
            self._render_static([station_name, message, screen_b[0], screen_b[1]])
            return
        self._start_ticker(ERROR_CYCLE_SECONDS, [screen_a, screen_b])

    def show_shutdown(self):
        self._cancel_pending()
        self._render_static(["À bientôt !", ""])
        self.set_backlight(True)

    def sleep(self):
        self._cancel_pending()
        self.set_backlight(False)

    # -- rendu bas niveau -------------------------------------------------

    def _render_static(self, lines: list[str]):
        for row in range(LCD_ROWS):
            self.lcd.write_row(row, _pad(lines[row] if row < len(lines) else ""))

    def _start_ticker(self, interval: float, screens: list[list[str]]):
        self._stop_ticker()
        stop = threading.Event()
        self._ticker_stop = stop

        def loop():
            i = 0
            while not stop.is_set():
                self._render_static(screens[i % len(screens)])
                i += 1
                stop.wait(interval)

        self._ticker_thread = threading.Thread(target=loop, daemon=True)
        self._ticker_thread.start()

    def _start_scroll(self, row: int, text: str):
        self._stop_ticker()
        stop = threading.Event()
        self._ticker_stop = stop
        looped = _strip_accents(text) + SCROLL_GAP

        def loop():
            offset = 0
            while not stop.is_set():
                window = (looped * 2)[offset : offset + LCD_COLS]
                self.lcd.write_row(row, window)
                offset = (offset + 1) % len(looped)
                stop.wait(SCROLL_INTERVAL_SECONDS)

        self._ticker_thread = threading.Thread(target=loop, daemon=True)
        self._ticker_thread.start()

    def _stop_ticker(self):
        """Attend la fin du thread (join) avant de rendre la main : sans ça,
        un rendu en vol (déjà passé le `while not stop.is_set()`) peut encore
        écrire sur le LCD juste après le nouvel écran demandé par l'appelant -
        constaté en simulation (show_error suivi de près par show_shutdown)."""
        if self._ticker_stop:
            self._ticker_stop.set()
        if self._ticker_thread:
            self._ticker_thread.join(timeout=1)
        self._ticker_thread = None
        self._ticker_stop = None
