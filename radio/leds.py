"""Deux LEDs de statut (plus une par station comme dans l'ancien projet,
la sélection ne passant plus par un switch dédié) :

  action  -> flash bref : confirme un changement de station ou une
             sauvegarde/chargement de favori.
  playing -> allumée en continu pendant la diffusion effective, clignote
             brièvement à chaque changement de titre/émission détecté.
"""

import threading

from gpiozero import LED

ACTION_PULSE_SECONDS = 0.15
TITLE_BLINK_SECONDS = 0.2


class StatusLeds:
    def __init__(self, action_pin: int, playing_pin: int):
        self._action = LED(action_pin)
        self._playing = LED(playing_pin)

    def pulse_action(self):
        """Flash bref, indépendant de tout autre état (action confirmée)."""
        self._action.on()
        threading.Timer(ACTION_PULSE_SECONDS, self._action.off).start()

    def set_playing(self, is_playing: bool):
        """Allume/éteint la LED lecture en continu (démarrage/arrêt/erreur)."""
        self._playing.value = is_playing

    def pulse_title_change(self):
        """Clignotement bref sans perdre l'état "allumée en continu" tant
        que la lecture se poursuit - à n'appeler que si is_playing est vrai."""
        self._playing.off()
        threading.Timer(TITLE_BLINK_SECONDS, self._playing.on).start()

    def close(self):
        self._action.close()
        self._playing.close()
