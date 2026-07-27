"""Persistance légère de l'état applicatif (dernière station, dernier volume)
entre redémarrages, dans un fichier JSON sous var/."""

import json
import logging

from radio.config import ROOT

log = logging.getLogger(__name__)

STATE_FILE = ROOT / "var" / "state.json"


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        log.warning("État précédent illisible (%s), valeurs par défaut utilisées", e)
        return {}


def save_state(**kwargs):
    """Fusionne kwargs dans l'état existant et réécrit le fichier (écriture
    atomique via un fichier temporaire + rename, pour éviter un JSON
    tronqué si le Pi perd l'alimentation en pleine écriture)."""
    state = load_state()
    state.update(kwargs)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(STATE_FILE)
