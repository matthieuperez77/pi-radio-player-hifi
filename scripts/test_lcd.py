"""Test bas niveau de l'écran LCD : enchaîne les différents écrans (boot,
station, now playing avec défilement, erreur, shutdown) pour validation
visuelle rapide, sur le vrai LCD ou en simulation (var/preview/lcd.txt).

Usage : python3 scripts/test_lcd.py
"""

import getpass
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radio.display import Display
from radio.sysinfo import get_local_ip

FAKE_STATION = {"name": "France Musique La Jazz"}

display = Display()

print("1. boot")
display.show_boot()
time.sleep(2)

print("2. sélection station (toujours affichée)")
display.show_station(FAKE_STATION)
time.sleep(2)

print("3. now playing, texte court")
display.set_follow_playback(True)
display.show_now_playing(FAKE_STATION, "Jazz")
time.sleep(2)

print("4. now playing, texte long (défilement)")
display.show_now_playing(FAKE_STATION, "Un très long titre d'émission qui ne tient pas sur l'écran")
time.sleep(6)

print("5. erreur")
display.show_error(FAKE_STATION["name"], "Flux injoignable", get_local_ip(), getpass.getuser())
time.sleep(8)

print("6. extinction")
display.show_shutdown()
time.sleep(2)

display.sleep()
print("terminé")
