"""
config.py

Wszystkie wartości pobierane są ze zmiennych środowiskowych (ustawiasz je
w pliku .env lokalnie albo w panelu Render -> Environment).
Listy PARTIES i DEGREES edytujesz bezpośrednio tutaj.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ====== Discord ======
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# Opcjonalnie: ID serwera do szybkiej (natychmiastowej) synchronizacji komend
# podczas testów. Zostaw puste dla globalnej synchronizacji (do ok. 1h).
GUILD_ID = int(os.getenv("GUILD_ID", "0")) or None

# ====== Firebase Realtime Database ======
FIREBASE_URL = os.getenv("FIREBASE_URL", "").rstrip("/")
FIREBASE_SECRET = os.getenv("FIREBASE_SECRET", "")

# ====== Role ======
ROLE_VERIFIED_ID = int(os.getenv("ROLE_VERIFIED_ID", "0"))          # rola "Zweryfikowany"
ROLE_CITIZEN_ID = int(os.getenv("ROLE_CITIZEN_ID", "0"))            # rola "Obywatel"
ROLE_SENATOR_ID = int(os.getenv("ROLE_SENATOR_ID", "0"))            # opcjonalnie, 0 = wyłączone
ROLE_REPRESENTATIVE_ID = int(os.getenv("ROLE_REPRESENTATIVE_ID", "0"))  # opcjonalnie, 0 = wyłączone
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0"))                # rola administracji uprawniona do komend admin.

# ====== Kanały ======
APPLICATIONS_REVIEW_CHANNEL_ID = int(os.getenv("APPLICATIONS_REVIEW_CHANNEL_ID", "0"))

# ====== Listy do edycji ======
PARTIES = [
    "Partia Demokratyczna",
    "Partia Republikańska",
    "Partia Libertariańska",
    "Niezależny",
]

DEGREES = [
    "Brak",
    "Licencjat (Bachelor's Degree)",
    "Magister (Master's Degree)",
    "Doktor (Ph.D.)",
    "Profesor (Professor)",
]

POSITIONS = ["Senator", "Reprezentant"]
