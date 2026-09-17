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

def _parse_id_list(raw: str) -> list[int]:
    """Parsuje '111,222, 333' -> [111, 222, 333]. Puste/blednee wpisy sa pomijane."""
    return [int(part.strip()) for part in raw.split(",") if part.strip().isdigit()]


# ====== Role ======
ROLE_VERIFIED_ID = int(os.getenv("ROLE_VERIFIED_ID", "0"))          # rola "Zweryfikowany"
ROLE_CITIZEN_ID = int(os.getenv("ROLE_CITIZEN_ID", "0"))            # rola "Obywatel"

# Role nadawane PO AKCEPTACJI podania - moze byc ich dowolnie wiele,
# wpisane po przecinku w jednej zmiennej srodowiskowej, np.:
# ROLE_SENATOR_IDS=123456789012345678,234567890123456789
ROLE_SENATOR_IDS = _parse_id_list(os.getenv("ROLE_SENATOR_IDS", ""))
ROLE_REPRESENTATIVE_IDS = _parse_id_list(os.getenv("ROLE_REPRESENTATIVE_IDS", ""))

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

# Tag doklejany do nicku na serwerze w formacie "[TAG] Imie Nazwisko".
# Klucze musza dokladnie odpowiadac wartosciom z listy PARTIES.
PARTY_TAGS = {
    "Partia Demokratyczna": "DEM.",
    "Partia Republikańska": "REP.",
    "Partia Libertariańska": "LIB.",
    "Niezależny": "BEZP.",
}

DEGREES = [
    "Brak",
    "Licencjat (Bachelor's Degree)",
    "Magister (Master's Degree)",
    "Doktor (Ph.D.)",
    "Profesor (Professor)",
]

POSITIONS = ["Senator", "Reprezentant"]
