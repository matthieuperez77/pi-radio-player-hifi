"""Entrées physiques : deux encodeurs rotatifs (volume, changement de
station façon "tuner"), des boutons favoris (appui court/long) et le bouton
d'arrêt propre, repris tel quel de l'ancien projet."""

import logging

from gpiozero import Button, RotaryEncoder

log = logging.getLogger(__name__)


class VolumeEncoder:
    """Rotation = +/- `step` % de volume (clampé 0-100). Le bouton intégré
    bascule le mute (cf. RadioApp.on_toggle_mute) : volume mpv mis à 0 sur
    un appui, restauré au niveau précédent sur le suivant."""

    def __init__(self, clk_pin: int, dt_pin: int, sw_pin: int, on_change, on_toggle_mute, step: int = 2, initial_percent: int = 50):
        self.percent = initial_percent
        self._on_change = on_change
        self._step = step
        self._encoder = RotaryEncoder(clk_pin, dt_pin, bounce_time=0.01)
        self._encoder.when_rotated_clockwise = lambda: self._adjust(self._step)
        self._encoder.when_rotated_counter_clockwise = lambda: self._adjust(-self._step)
        self._button = Button(sw_pin, pull_up=True, bounce_time=0.05)
        self._button.when_pressed = on_toggle_mute

    def _adjust(self, delta: int):
        self.percent = max(0, min(100, self.percent + delta))
        self._on_change(self.percent)

    def close(self):
        self._encoder.close()
        self._button.close()


class StationEncoder:
    """Rotation = changement immédiat de station (cran suivant/précédent,
    comportement "tuner vintage", pas de confirmation). Appui long sur le
    bouton intégré = bascule le mode LCD actif/éteint pendant l'écoute."""

    def __init__(self, clk_pin: int, dt_pin: int, sw_pin: int, on_next, on_previous, on_toggle_display, hold_time: float = 1.5):
        self._encoder = RotaryEncoder(clk_pin, dt_pin, bounce_time=0.01)
        self._encoder.when_rotated_clockwise = on_next
        self._encoder.when_rotated_counter_clockwise = on_previous
        self._button = Button(sw_pin, pull_up=True, hold_time=hold_time, hold_repeat=False, bounce_time=0.05)
        self._button.when_held = on_toggle_display

    def close(self):
        self._encoder.close()
        self._button.close()


class FavoriteButton:
    """Un slot favori : appui court -> charge la station enregistrée, appui
    long -> enregistre la station en cours dans ce slot. `when_held` et
    `when_released` de gpiozero ne s'excluent pas nativement : on suit
    `_held` pour ne déclencher le chargement que si la tenue n'a pas déjà
    déclenché la sauvegarde (même pattern que ShutdownButton/hold_time)."""

    def __init__(self, pin: int, slot: int, on_load, on_save, hold_time: float = 1.2):
        self.slot = slot
        self._on_load = on_load
        self._on_save = on_save
        self._held = False
        self._button = Button(pin, pull_up=True, hold_time=hold_time, hold_repeat=False, bounce_time=0.05)
        self._button.when_held = self._on_hold
        self._button.when_released = self._on_release

    def _on_hold(self):
        self._held = True
        self._on_save(self.slot)

    def _on_release(self):
        if not self._held:
            self._on_load(self.slot)
        self._held = False

    def close(self):
        self._button.close()


class FavoriteButtons:
    def __init__(self, pins: list[int], on_load, on_save):
        self._buttons = [FavoriteButton(pin, slot, on_load, on_save) for slot, pin in enumerate(pins, start=1)]

    def close(self):
        for button in self._buttons:
            button.close()


class ShutdownButton:
    """Bouton poussoir maintenu ~0.5s pour déclencher l'arrêt propre du
    Raspberry Pi (hold_time évite un déclenchement sur un simple effleurement,
    sans forcer un maintien long)."""

    def __init__(self, pin: int, on_shutdown):
        self._button = Button(pin, pull_up=True, hold_time=0.5, bounce_time=0.05)
        self._button.when_held = on_shutdown

    def close(self):
        self._button.close()
