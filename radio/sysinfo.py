"""Infos système affichées sur l'écran d'erreur pour faciliter le dépannage
par SSH (IP + utilisateur qui fait tourner le service)."""

import getpass
import socket


def get_local_ip() -> str | None:
    """IP locale utilisée pour joindre l'extérieur. Le connect() UDP ne
    transmet rien sur le réseau, il consulte juste la table de routage
    locale - fonctionne même sans accès internet réel, tant qu'il y a une
    route par défaut (LAN)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            return None


def get_username() -> str:
    return getpass.getuser()
