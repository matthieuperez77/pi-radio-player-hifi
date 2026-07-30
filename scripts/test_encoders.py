"""Test bas niveau des 2 encodeurs rotatifs : affiche chaque cran (volume,
navigation station) et chaque appui/maintien des boutons intégrés. Permet de
vérifier le câblage (CLK/DT inversés = sens de rotation inversé) sans
dépendre du reste de l'appli.

Usage : python3 scripts/test_encoders.py
Arrêt : Ctrl+C
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radio import config
from radio.input import StationEncoder, VolumeEncoder

# Le mute reel (mise a 0/restauration du volume mpv, cf. RadioApp) depend
# du Player, absent de ce script bas niveau : on se contente d'afficher le
# toggle pour verifier le bouton.
muted = False


def on_toggle_mute():
    global muted
    muted = not muted
    print(f"[volume] bouton -> mute {'ACTIF' if muted else 'inactif'}")


volume = VolumeEncoder(
    config.VOL_ENCODER_CLK_PIN,
    config.VOL_ENCODER_DT_PIN,
    config.VOL_ENCODER_SW_PIN,
    on_change=lambda percent: print(f"[volume] {percent}%"),
    on_toggle_mute=on_toggle_mute,
)

station_encoder = StationEncoder(
    config.STATION_ENCODER_CLK_PIN,
    config.STATION_ENCODER_DT_PIN,
    config.STATION_ENCODER_SW_PIN,
    on_next=lambda: print("[station] cran suivant"),
    on_previous=lambda: print("[station] cran précédent"),
    on_toggle_display=lambda: print("[station] appui long -> toggle LCD"),
)

print("encodeurs surveillés : tourne/appuie sur chacun (Ctrl+C pour arrêter)")
print(f"  volume  : CLK=GPIO{config.VOL_ENCODER_CLK_PIN} DT=GPIO{config.VOL_ENCODER_DT_PIN} SW=GPIO{config.VOL_ENCODER_SW_PIN}")
print(f"  station : CLK=GPIO{config.STATION_ENCODER_CLK_PIN} DT=GPIO{config.STATION_ENCODER_DT_PIN} SW=GPIO{config.STATION_ENCODER_SW_PIN}")

try:
    while True:
        time.sleep(0.2)
except KeyboardInterrupt:
    pass
finally:
    volume.close()
    station_encoder.close()
