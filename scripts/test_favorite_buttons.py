"""Test bas niveau des boutons favoris : affiche "chargement" sur appui
court et "enregistrement" sur appui long (~1.2s), pour vérifier chaque
connexion sans dépendre du reste de l'appli (pas d'audio, pas d'écran).

Usage : python3 scripts/test_favorite_buttons.py
Arrêt : Ctrl+C
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radio import config
from radio.input import FavoriteButtons

buttons = FavoriteButtons(
    config.FAVORITE_BUTTON_PINS,
    on_load=lambda slot: print(f"[favori {slot}] appui court -> chargement"),
    on_save=lambda slot: print(f"[favori {slot}] appui long -> enregistrement"),
)

print(f"{len(config.FAVORITE_BUTTON_PINS)} boutons favoris surveillés (Ctrl+C pour arrêter) :")
for slot, pin in enumerate(config.FAVORITE_BUTTON_PINS, start=1):
    print(f"  - favori {slot} -> GPIO{pin}")

try:
    while True:
        time.sleep(0.2)
except KeyboardInterrupt:
    pass
finally:
    buttons.close()
