"""Test bas niveau des 2 LEDs de statut (action / lecture) : les allume
tour à tour pour vérifier chaque connexion (bonne broche, bon sens,
résistance en place) au fur et à mesure du câblage.

Usage : python3 scripts/test_leds.py
Arrêt : Ctrl+C
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radio import config
from radio.leds import StatusLeds

leds = StatusLeds(config.ACTION_LED_PIN, config.PLAYING_LED_PIN)

print(f"LED action (GPIO{config.ACTION_LED_PIN}) et LED lecture (GPIO{config.PLAYING_LED_PIN})")
print("boucle : flash action, puis lecture allumée 1.5s avec un clignotement titre (Ctrl+C pour arrêter)")

try:
    while True:
        print("  -> flash action")
        leds.pulse_action()
        time.sleep(1)
        print("  -> lecture ON")
        leds.set_playing(True)
        time.sleep(1.5)
        print("  -> clignotement changement de titre")
        leds.pulse_title_change()
        time.sleep(1.5)
        print("  -> lecture OFF")
        leds.set_playing(False)
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    leds.close()
