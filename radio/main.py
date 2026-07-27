"""Orchestration : rotation de l'encodeur station -> changement immédiat de
station façon "tuner" (LED + LCD + lecture), boutons favoris (charge/enregistre),
encodeur volume event-driven, et repli automatique sur les flux de qualité
dégradée d'une station (stream_urls) avant d'afficher une erreur."""

import logging
import signal
import subprocess
import threading

from radio import config
from radio.audio import HatMute, Player
from radio.config import load_stations
from radio.display import Display
from radio.input import FavoriteButtons, ShutdownButton, StationEncoder, VolumeEncoder
from radio.leds import StatusLeds
from radio.metadata import get_current_emission
from radio.state import load_state, save_state
from radio.sysinfo import get_local_ip, get_username

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


class RadioApp:
    def __init__(self):
        self.stations, self.refresh_interval = load_stations()
        self.by_id = {s["id"]: s for s in self.stations}
        self.station_index = {s["id"]: i for i, s in enumerate(self.stations)}
        self.current_station = None
        self.current_index = 0
        self.shown_emission_text = None  # évite un refresh LCD si rien n'a changé
        self.stream_error = False  # bloque le refresh périodique tant que l'erreur est affichée
        self._stream_attempt = 0  # index courant dans stream_urls, pour le repli qualité
        self._lock = threading.Lock()
        self._stop = threading.Event()

        self.state = load_state()  # dernier run : station, volume, favoris, préférence LCD
        self.favorites = self.state.get("favorites", {})
        self.lcd_follow_playback = self.state.get("lcd_follow_playback", True)
        self.muted = False  # jamais persisté : on redémarre toujours démuté

        self.player = Player()
        self.player.on_error = self._on_stream_error
        self.hat_mute = HatMute()

        self.display = Display()
        self.display.set_follow_playback(self.lcd_follow_playback)
        self.display.show_boot()

        self.leds = StatusLeds(config.ACTION_LED_PIN, config.PLAYING_LED_PIN)

        volume_percent = self.state.get("volume_percent", 50)
        self.volume = VolumeEncoder(
            config.VOL_ENCODER_CLK_PIN,
            config.VOL_ENCODER_DT_PIN,
            config.VOL_ENCODER_SW_PIN,
            self.on_volume_change,
            self.on_toggle_mute,
            initial_percent=volume_percent,
        )
        self.player.set_volume(self.volume.percent)

        self.station_encoder = StationEncoder(
            config.STATION_ENCODER_CLK_PIN,
            config.STATION_ENCODER_DT_PIN,
            config.STATION_ENCODER_SW_PIN,
            on_next=lambda: self._select_by_offset(1),
            on_previous=lambda: self._select_by_offset(-1),
            on_toggle_display=self.on_toggle_lcd_follow,
        )

        self.favorite_buttons = FavoriteButtons(config.FAVORITE_BUTTON_PINS, self.on_favorite_load, self.on_favorite_save)
        self.shutdown_button = ShutdownButton(config.SHUTDOWN_PIN, self.on_shutdown_button)

    def on_select(self, station_id: str):
        station = self.by_id[station_id]
        log.info("Station sélectionnée : %s", station["name"])
        with self._lock:
            self.current_station = station
            self.current_index = self.station_index[station_id]
            self.shown_emission_text = None
            self.stream_error = False
            self._stream_attempt = 0
            self.leds.pulse_action()
            self.leds.set_playing(True)
            self.player.play(station["stream_urls"][0], station.get("stream_needs_ytdl", False))
            self.display.show_station(station)
        save_state(station_id=station_id)

    def _select_by_offset(self, offset: int):
        with self._lock:
            idx = (self.current_index + offset) % len(self.stations)
            next_id = self.stations[idx]["id"]
        self.on_select(next_id)

    def on_favorite_load(self, slot: int):
        station_id = self.favorites.get(str(slot))
        if station_id in self.by_id:
            self.on_select(station_id)
        else:
            log.info("Favori %d vide", slot)

    def on_favorite_save(self, slot: int):
        with self._lock:
            station = self.current_station
            if station is None:
                return
            self.favorites[str(slot)] = station["id"]
        save_state(favorites=self.favorites)
        self.leds.pulse_action()
        log.info("Favori %d enregistré : %s", slot, station["name"])

    def on_toggle_lcd_follow(self):
        self.lcd_follow_playback = not self.lcd_follow_playback
        self.display.set_follow_playback(self.lcd_follow_playback)
        save_state(lcd_follow_playback=self.lcd_follow_playback)
        log.info("LCD pendant l'écoute : %s", "actif" if self.lcd_follow_playback else "éteint")

    def on_volume_change(self, percent: int):
        self.player.set_volume(percent)
        save_state(volume_percent=percent)

    def on_toggle_mute(self):
        self.muted = not self.muted
        self.hat_mute.set_muted(self.muted)
        self.leds.set_muted(self.muted)
        log.info("Mute matériel : %s", "actif" if self.muted else "inactif")

    def refresh_metadata(self):
        with self._lock:
            station = self.current_station
            if station is None or self.stream_error:
                return
        emission_text = get_current_emission(station)
        with self._lock:
            if self.current_station is not station:  # changé entretemps
                return
            if emission_text == self.shown_emission_text:
                return  # rien de neuf, on évite un rafraîchissement LCD inutile
            self.shown_emission_text = emission_text
            self.display.show_now_playing(station, emission_text)
        self.leds.pulse_title_change()

    def _on_stream_error(self, message: str):
        with self._lock:
            station = self.current_station
            if station is None or self.stream_error:
                return
            urls = station["stream_urls"]
            next_attempt = self._stream_attempt + 1
            if next_attempt < len(urls):
                self._stream_attempt = next_attempt
                log.warning(
                    "Flux injoignable pour %s (%s), repli qualité %d/%d",
                    station["name"], message, next_attempt + 1, len(urls),
                )
                self.player.play(urls[next_attempt], station.get("stream_needs_ytdl", False))
                return
            self.stream_error = True
        log.warning("Tous les flux de %s sont injoignables : %s", station["name"], message)
        self.leds.set_playing(False)
        ip, user = get_local_ip(), get_username()
        with self._lock:
            if self.current_station is not station:  # station changée entretemps
                return
            self.display.show_error(station["name"], "Flux injoignable", ip, user)

    def run(self):
        start_id = self.state.get("station_id")
        if start_id not in self.by_id:
            start_id = self.stations[0]["id"]
        self.on_select(start_id)
        while not self._stop.is_set():
            self._stop.wait(self.refresh_interval)
            if not self._stop.is_set():
                self.refresh_metadata()

    def shutdown(self, *_):
        log.info("Arrêt en cours...")
        self._stop.set()
        self.station_encoder.close()
        self.volume.close()
        self.favorite_buttons.close()
        self.shutdown_button.close()
        self.leds.close()
        self.display.sleep()
        self.hat_mute.close()
        self.player.close()

    def on_shutdown_button(self):
        """Bouton d'arrêt maintenu ~2s : affiche l'écran d'extinction puis
        éteint le Raspberry Pi. Le reste du nettoyage (GPIO/audio) est fait
        par `shutdown()`, appelé normalement via SIGTERM quand systemd
        arrête le service pendant l'extinction du système - pas dupliqué ici
        pour éviter de fermer le bouton depuis son propre thread d'évènement."""
        log.info("Bouton d'arrêt maintenu -> affichage écran d'extinction et arrêt")
        self.display.show_shutdown()
        self.display.sleep()
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)


def main():
    app = RadioApp()
    signal.signal(signal.SIGTERM, app.shutdown)
    signal.signal(signal.SIGINT, app.shutdown)
    app.run()


if __name__ == "__main__":
    main()
