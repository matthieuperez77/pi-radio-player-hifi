from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
STATIONS_FILE = ROOT / "stations.yaml"

# I2C (bus 1, pins standard GPIO2/GPIO3) - partagé par le LCD caractères.
# Adresse à confirmer sur le matériel réel avec `i2cdetect -y 1` (backpack
# PCF8574 : 0x27 le plus courant, 0x3f sur certains clones type Qapass).
I2C_BUS = 1
LCD_I2C_ADDRESS = 0x27
LCD_COLS = 16
LCD_ROWS = 2

# GPIO liés au HAT InnoMaker DAC Mini (PCM5122) - confirmé par le manuel
# constructeur (UserManual, tableau §3.2) le 2026-07-27 :
#   GPIO2/3   (SDA1/SCL1)  -> I2C du DAC (même bus que le LCD, adresses
#                             différentes donc pas de conflit)
#   GPIO18/19/21 (BCLK/LRCLK/DOUT) -> I2S, piloté par le HAT
#   GPIO6     -> pin de mute côté HAT, déjà revendiqué par le kernel au
#                démarrage via le dtoverlay allo-boss-dac-pcm512x-audio
#                (confirmé par `gpioinfo` le 2026-07-30, consumer="mute") -
#                on ne le pilote PAS depuis l'appli (mute géré en logiciel
#                côté mpv, cf. RadioApp.on_toggle_mute), on l'évite juste
#                pour ne pas rentrer en conflit avec le driver noyau
#   GPIO26    -> réservé récepteur IR (non câblé par défaut sur la variante
#                Mini, mais réservé par le constructeur - on l'évite pour
#                garder l'option ouverte)
#   GPIO0/1   (ID_SD/ID_SC) -> réservés HAT EEPROM, convention 40-pin standard
# Ne JAMAIS réutiliser GPIO2/3/18/19/21/26/0/1 pour un bouton, une LED ou un
# encodeur.
#
# Encodeur volume (gpiozero.RotaryEncoder + bouton poussoir intégré).
VOL_ENCODER_CLK_PIN = 17
VOL_ENCODER_DT_PIN = 27
VOL_ENCODER_SW_PIN = 22

# Encodeur de changement de station, façon "tuner" (cf. StationEncoder).
# Le bouton intégré sert au bascule LCD actif/éteint pendant l'écoute.
STATION_ENCODER_CLK_PIN = 5
STATION_ENCODER_DT_PIN = 7
STATION_ENCODER_SW_PIN = 13

# 4 boutons favoris (appui court = charger, appui long = enregistrer),
# indexés 1 à 4 dans cet ordre.
FAVORITE_BUTTON_PINS = [16, 12, 25, 24]

# Bouton d'arrêt propre (maintien ~2s). GPIO14 libre : UART désactivé,
# repris de l'ancien projet (radio-epaper) où ce choix a été validé.
SHUTDOWN_PIN = 14

# LEDs : "action" (confirmation changement de station / favori),
# "playing" (allumée pendant la diffusion, clignote au changement de titre,
# clignote LENTEMENT tant que le mute (cf. RadioApp.on_toggle_mute) est actif).
ACTION_LED_PIN = 23
PLAYING_LED_PIN = 4

# Device ALSA explicite pour mpv. Le HAT InnoMaker DAC Mini apparaît en tant
# que carte "BossDAC" une fois l'overlay chargé (confirmé par `aplay -l` /
# `cat /proc/asound/cards` le 2026-07-30, carte 2). Nécessaire : sans ça,
# mpv/ALSA route vers le jack analogique intégré du Pi (carte 1, "bcm2835
# Headphones") plutôt que le HAT, avec un grésillement caractéristique du
# petit DAC PWM du Pi (constaté le 2026-07-30).
AUDIO_DEVICE = "alsa/hw:CARD=BossDAC,DEV=0"


def load_stations():
    with open(STATIONS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["stations"], data["refresh_interval_seconds"]
