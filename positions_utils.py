"""
positions_utils.py

Wyznacza "najwyzsze zajmowane stanowisko" danej osoby na podstawie jej
AKTUALNYCH rol na Discordzie:
- role z ROLE_SENATOR_IDS / ROLE_REPRESENTATIVE_IDS (config.py) -> automatycznie
  "Senator" / "Reprezentant" (nadawane przez bota po akceptacji podania)
- pozostale mapowania rola -> nazwa stanowiska ustawia administracja komenda
  /stan i sa trzymane w Firebase pod /position_roles/{role_id}

"Najwyzsze" stanowisko to takie, ktorego rola ma najwyzsza pozycje w
hierarchii rol serwera (Discord sam o to dba - admin ustawia kolejnosc,
przeciagajac role w Ustawienia serwera -> Role). Dzieki temu nie trzeba
osobno konfigurowac "rangi" kazdego stanowiska - kolejnosc rol na
Discordzie JEST ta ranga.
"""

import discord

import config
import firebase_client as db


async def get_highest_position(member: discord.Member) -> str | None:
    """Zwraca nazwe najwyzszego stanowiska danej osoby, albo None jesli zadna
    z jej rol nie jest zmapowana na stanowisko."""
    if member is None:
        return None

    position_roles = await db.get("position_roles") or {}

    candidates = []  # (pozycja_roli_w_hierarchii, nazwa_stanowiska)

    for role in member.roles:
        title = None

        if role.id in config.ROLE_SENATOR_IDS:
            title = "Senator"
        elif role.id in config.ROLE_REPRESENTATIVE_IDS:
            title = "Reprezentant"

        mapped_title = position_roles.get(str(role.id))
        if mapped_title:
            title = mapped_title  # mapowanie z /stan nadpisuje nazwe automatyczna

        if title:
            candidates.append((role.position, title))

    if not candidates:
        return None

    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return candidates[0][1]
