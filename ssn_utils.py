"""
ssn_utils.py

Generuje fikcyjny, unikalny numer SSN w formacie AAA-BB-CCCC na potrzeby
roleplay. Dwie pierwsze cyfry pierwszego bloku pochodzą z roku urodzenia
postaci, reszta jest losowa. Unikalność sprawdzana jest w Firebase.
"""

import random

import firebase_client as db


async def generate_unique_ssn(birth_year: int) -> str:
    year_part = f"{birth_year % 100:02d}"

    for _ in range(50):  # praktyczny limit prób, kolizje są bardzo mało prawdopodobne
        part1 = f"{year_part}{random.randint(0, 9)}"
        part2 = f"{random.randint(0, 99):02d}"
        part3 = f"{random.randint(0, 9999):04d}"
        ssn = f"{part1}-{part2}-{part3}"

        existing = await db.get(f"ssn_index/{ssn.replace('-', '_')}")
        if not existing:
            return ssn

    raise RuntimeError("Nie udało się wygenerować unikalnego SSN — spróbuj ponownie.")


async def reserve_ssn(ssn: str, discord_id: int) -> None:
    await db.put(f"ssn_index/{ssn.replace('-', '_')}", str(discord_id))
