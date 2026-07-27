# Lecteur radio HiFi (LCD + encodeurs)

Lecteur radio web sur Raspberry Pi 3, dans le même esprit "low-tech" que le
premier projet ([`pi-radio-player-with-epaper-hat`](https://github.com/matthieuperez77/pi-radio-player-with-epaper-hat))
mais avec un matériel différent : écran LCD caractères au lieu de l'e-Paper,
encodeurs rotatifs au lieu du potentiomètre, sortie audio via un HAT Hi-Fi
dédié, et un choix de stations bien plus large (réseau national Radio France
+ sélection internationale).

## Matériel

| Élément | Détail |
|---|---|
| Carte | Raspberry Pi 3, Debian 13 (Trixie) |
| Écran | LCD caractères I2C (Qapass, backpack PCF8574), 16x2 par défaut — à ajuster dans `config.py` si finalement 20x4 |
| Encodeur volume | Rotatif, +/- 2% par cran, bouton intégré = mute/unmute |
| Encodeur station | Rotatif façon "tuner vintage" : chaque cran change immédiatement de station et lance la lecture ; bouton intégré (appui long ~1.5s) = bascule LCD actif/éteint pendant l'écoute |
| Boutons favoris | 4 boutons poussoir : appui court = charge le favori du slot, appui long (~1.2s) = enregistre la station en cours dans le slot |
| Bouton d'arrêt | 1 bouton poussoir dédié, maintien ~2s → arrêt propre du Raspberry Pi |
| LEDs | 2 : "action" (flash bref à un changement de station ou une action favori), "lecture" (allumée en continu pendant la diffusion, clignote au changement de titre) |
| Audio | HAT InnoMaker DAC Mini (PCM5122, I2S) |

## Stations

33 stations dans [`stations.yaml`](stations.yaml) :

- **Réseau national Radio France** (24 flux) : France Inter, France Info,
  France Culture, Mouv', France Musique + 8 webradios thématiques, FIP + 11
  webradios thématiques. Chaque station a une liste `stream_urls` ordonnée
  (`hifi.aac` 192kbps → `midfi.mp3` 128kbps → `lofi.mp3` 32kbps) : `Player`
  se replie automatiquement sur le candidat suivant si mpv signale une
  erreur de lecture, avant d'afficher l'écran d'erreur.
  Les 44 antennes locales du réseau "ici" (ex-France Bleu) sont **hors
  périmètre** par choix (infos très locales, moins pertinentes en écoute
  domestique).
- **Sélection internationale** (9 flux, genres jazz/classique,
  rock/pop/alternatif/électro, world/divers) : Radio Swiss Jazz, Radio
  Swiss Classic, Radio Paradise (+ mix Rock et World/Etc), SomaFM (Groove
  Salad, Drone Zone, Suburbs of Goa). **Ces flux tiers n'ont pas encore été
  validés en conditions réelles** (moins stables que Radio France) — à
  tester avec mpv avant de les considérer fiables. BBC volontairement
  exclue (déjà source de problèmes récurrents dans le premier projet).
- Métadonnées "case en cours" (`radiofrance_livemeta`) confirmées
  seulement pour France Musique (id 4) et FIP (id 7) ; les autres stations
  Radio France démarrent en `metadata.type: none` faute d'id vérifié — voir
  le commentaire en tête de `stations.yaml` pour compléter au cas par cas.

## Architecture logicielle

```
radio/
  config.py     constantes (pins, bus I2C, LCD, device audio), chargement de stations.yaml
  audio.py      pilotage mpv (démon + socket IPC JSON), détection d'erreur de lecture
  metadata.py   récupération du nom de la case en cours (Radio France)
  display.py    composition des écrans et pilotage du LCD caractères (+ mode simulation)
  input.py      VolumeEncoder, StationEncoder, FavoriteButtons, ShutdownButton
  leds.py       StatusLeds (action / lecture)
  state.py      persistance (station, volume, favoris, préférence LCD) entre redémarrages
  sysinfo.py    IP locale + utilisateur (pour l'écran d'erreur)
  main.py       orchestration (RadioApp), point d'entrée du service
scripts/        scripts de diagnostic matériel (voir plus bas)
systemd/        unit file du service
```

**Principe général** : tourner l'encodeur station change immédiatement de
station (LED + LCD + audio), sans confirmation. Le nom de la station
s'affiche toujours au changement, quel que soit le réglage LCD ; le nom de
la case en cours n'est lui rafraîchi que périodiquement
(`refresh_interval_seconds`, 10 min par défaut) et seulement si le texte a
changé.

## Câblage / GPIO (numérotation BCM)

| Fonction | GPIO | Notes |
|---|---|---|
| I2C (LCD) | 2 (SDA), 3 (SCL) | Bus **I2C 1** — nécessite `dtparam=i2c_arm=on` (voir Installation) |
| I2S (HAT InnoMaker DAC Mini) | 18, 19, 20, 21 | piloté par le HAT/overlay, **ne jamais réutiliser** ces GPIO pour un bouton/LED/encodeur |
| Encodeur volume | 17 (CLK), 27 (DT), 22 (SW) | |
| Encodeur station | 5 (CLK), 6 (DT), 13 (SW) | |
| Favori 1 / 2 / 3 / 4 | 16, 12, 25, 24 | |
| Bouton d'arrêt | 14 | UART désactivé sur cette machine, GPIO libre |
| LED action | 23 | |
| LED lecture | 26 | |

Tous les pins ci-dessus sont des valeurs de départ dans `config.py` — à
ajuster si le câblage réel diffère (aucune autre logique n'en dépend).

## Installation

Constaté sur le Raspberry Pi cible le 2026-07-27, avant câblage :

- `/dev/i2c-2` existe déjà mais n'est câblé à rien (comme sur le premier Pi) ;
  `dtparam=i2c_arm=on` est **commenté** dans `/boot/firmware/config.txt` →
  à décommenter pour activer le bus I2C 1 (GPIO2/3, utilisé par le LCD).
- `dtparam=i2s=on` est **commenté** → à décommenter pour le HAT InnoMaker
  DAC Mini (PCM5122), en plus de l'overlay du DAC lui-même (probablement
  `dtoverlay=hifiberry-dac`, chip compatible - **à confirmer auprès de la
  documentation InnoMaker avant de figer**, puis noter le résultat ici une
  fois validé sur le matériel).
- `mpv` n'est pas installé (`apt install mpv`).
- Un redémarrage est nécessaire après modification de `config.txt`.

Étapes :

```bash
sudo apt install mpv i2c-tools
sudo raspi-config nonint do_i2c 0   # ou décommenter dtparam=i2c_arm=on à la main
# ajouter dtparam=i2s=on + dtoverlay=hifiberry-dac (à confirmer) dans /boot/firmware/config.txt
sudo reboot

# après redémarrage : vérifier l'adresse I2C du LCD (0x27 le plus courant,
# 0x3f sur certains clones) et la mettre à jour dans radio/config.py si besoin
i2cdetect -y 1

# vérifier la carte son résultante et renseigner AUDIO_DEVICE dans
# radio/config.py seulement si ce n'est pas la carte par défaut
aplay -l

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Lancement manuel (hors systemd, pour valider avant d'installer le service) :

```bash
.venv/bin/python3 -m radio.main
```

Puis service systemd :

```bash
sudo cp systemd/radio-hifi.service /etc/systemd/system/
sudo systemctl enable --now radio-hifi.service
```

## Scripts de diagnostic matériel

Dans `scripts/`, à lancer indépendamment du service pour vérifier le
câblage au fur et à mesure (voir l'en-tête de chaque fichier) :

- `test_encoders.py` — crans + boutons intégrés des 2 encodeurs
- `test_favorite_buttons.py` — appui court/long des 4 boutons favoris
- `test_leds.py` — LEDs action/lecture
- `test_shutdown_button.py` — maintien du bouton d'arrêt (simulé, n'éteint pas)
- `test_lcd.py` — enchaîne tous les écrans (boot, station, now playing avec
  défilement, erreur, extinction)

## Extension future (non construite dans cette passe)

Une interface web locale pour éditer la liste des stations depuis le LAN a
été envisagée mais volontairement différée : le risque principal est un
service non authentifié exposé sur le réseau local. À reprendre plus tard
seulement avec une vraie réflexion d'accès (bind `127.0.0.1` par défaut,
ou authentification basique / allowlist IP si exposée sur le LAN).
