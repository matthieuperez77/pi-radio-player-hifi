"""Récupération du nom de l'émission (case récurrente) en cours par station.

Deux sources possibles (cf. stations.yaml / metadata.type) :
  radiofrance_livemeta -> titleConcept de la case en cours, horodaté
  none                  -> pas de métadonnée disponible (écran : logo + nom
                            de station seuls)
"""

import logging
import time

import requests

log = logging.getLogger(__name__)

RADIOFRANCE_LIVEMETA_URL = "https://api.radiofrance.fr/livemeta/pull/{station_id}"

HTTP_TIMEOUT = 8


def fetch_radiofrance(station_id: int):
    url = RADIOFRANCE_LIVEMETA_URL.format(station_id=station_id)
    resp = requests.get(url, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    now = time.time()
    # Les steps s'emboîtent (émission > morceau) : on ne veut que le nom de
    # la case récurrente (titleConcept), donc on prend le step le moins
    # profond parmi ceux en cours. Si ce step n'a pas de titleConcept (ex.
    # simple rotation musicale sans case nommée), on n'affiche rien plutôt
    # que de se rabattre sur un titre de morceau.
    current = [
        s for s in data.get("steps", {}).values()
        if s.get("start", 0) <= now < s.get("end", 0)
    ]
    if not current:
        return None
    current.sort(key=lambda s: s.get("depth", 0))
    return current[0].get("titleConcept") or None


FETCHERS = {
    "radiofrance_livemeta": lambda m: fetch_radiofrance(m["station_id"]),
    "none": lambda m: None,
}


def get_current_emission(station: dict):
    meta = station["metadata"]
    try:
        return FETCHERS[meta["type"]](meta)
    except (requests.RequestException, OSError) as exc:
        log.warning("Échec récupération métadonnées pour %s: %s", station["id"], exc)
        return None
