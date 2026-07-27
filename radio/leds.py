"""Deux LEDs de statut (plus une par station comme dans l'ancien projet,
la sélection ne passant plus par un switch dédié) :

  action  -> flash bref : confirme un changement de station ou une
             sauvegarde/chargement de favori.
  playing -> allumée en continu pendant la diffusion effective, clignote
             brièvement à chaque changement de titre/émission détecté,
             clignote LENTEMENT en continu tant que le mute matériel est actif.
"""

import threading

from gpiozero import LED

ACTION_PULSE_SECONDS = 0.15
TITLE_BLINK_SECONDS = 0.2
MUTE_BLINK_SECONDS = 0.6


class StatusLeds:
    def __init__(self, action_pin: int, playing_pin: int):
        self._action = LED(action_pin)
        self._playing = LED(playing_pin)
        self._is_playing = False
        self._is_muted = False

    def pulse_action(self):
        """Flash bref, indépendant de tout autre état (action confirmée)."""
        self._action.on()
        threading.Timer(ACTION_PULSE_SECONDS, self._action.off).start()

    def set_playing(self, is_playing: bool):
        """Allume/éteint la LED lecture en continu (démarrage/arrêt/erreur),
        sauf si le mute est actif (le clignotement lent prime)."""
        self._is_playing = is_playing
        self._refresh()

    def set_muted(self, is_muted: bool):
        """Bascule le clignotement lent qui signale le mute matériel actif."""
        self._is_muted = is_muted
        self._refresh()

    def pulse_title_change(self):
        """Clignotement bref sans perdre l'état "allumée en continu" tant
        que la lecture se poursuit - à n'appeler que si is_playing est vrai.
        Sans effet si le mute est actif (pas de double signal sur la LED)."""
        if self._is_muted:
            return
        self._playing.off()
        threading.Timer(TITLE_BLINK_SECONDS, self._playing.on).start()

    def _refresh(self):
        if self._is_muted:
            self._playing.blink(on_time=MUTE_BLINK_SECONDS, off_time=MUTE_BLINK_SECONDS, background=True)
        elif self._is_playing:
            self._playing.on()
        else:
            self._playing.off()

    def close(self):
        self._action.close()
        self._playing.close()
