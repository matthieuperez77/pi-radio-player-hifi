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

# GPIO réservés par le HAT InnoMaker DAC Mini (PCM5122) - confirmé par le
# manuel constructeur (UserManual, tableau §3.2) le 2026-07-27 :
#   GPIO2/3   (SDA1/SCL1)  -> I2C du DAC (même bus que le LCD, adresses
#                             différentes donc pas de conflit)
#   GPIO18/19/21 (BCLK/LRCLK/DOUT) -> I2S, piloté par le HAT
#   GPIO6     -> pin de mute du DAC, ACTIVEMENT piloté par le HAT
#   GPIO26    -> réservé récepteur IR (non câblé par défaut sur la variante
#                Mini, mais réservé par le constructeur - on l'évite pour
#                garder l'option ouverte)
#   GPIO0/1   (ID_SD/ID_SC) -> réservés HAT EEPROM, convention 40-pin standard
# Ne JAMAIS réutiliser ces GPIO pour un bouton, une LED ou un encodeur.
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
# "playing" (allumée pendant la diffusion, clignote au changement de titre).
ACTION_LED_PIN = 23
PLAYING_LED_PIN = 4

# Device ALSA explicite pour mpv. Le HAT InnoMaker DAC Mini apparaît en tant
# que carte "BossDAC" une fois l'overlay chargé (cf. `aplay -l` /
# `cat /proc/asound/cards`), ex. "alsa/hw:CARD=BossDAC,DEV=0" - à renseigner
# seulement si ce n'est pas le device par défaut du système.
# None = laisse mpv/ALSA choisir le défaut.
AUDIO_DEVICE = None


def load_stations():
    with open(STATIONS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["stations"], data["refresh_interval_seconds"]
