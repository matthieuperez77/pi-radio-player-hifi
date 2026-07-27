"""Test bas niveau du bouton d'arrêt : affiche un message quand un maintien
~2s est détecté, au lieu de vraiment éteindre le Pi. Permet de vérifier le
câblage sans devoir relancer la session à chaque essai.

Usage : python3 scripts/test_shutdown_button.py
Arrêt : Ctrl+C
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radio.config import SHUTDOWN_PIN
from radio.input import ShutdownButton


def on_shutdown():
    print(f"maintien détecté sur GPIO{SHUTDOWN_PIN} -> shutdown (simulé, rien n'est éteint)")


button = ShutdownButton(SHUTDOWN_PIN, on_shutdown)
print(f"bouton d'arrêt surveillé sur GPIO{SHUTDOWN_PIN}, maintiens ~2s (Ctrl+C pour arrêter)")

try:
    while True:
        time.sleep(0.2)
except KeyboardInterrupt:
    pass
finally:
    button.close()
