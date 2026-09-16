"""
nickname_utils.py

Buduje i ustawia nick na serwerze w formacie:
[TAG_PARTII] Imie Nazwisko

Discord ogranicza nick do 32 znakow - jesli imie+nazwisko sie nie miesci,
przycinamy je (tag partii nigdy nie jest ucinany).
"""

import logging

import discord

import config

log = logging.getLogger("obywatel-bot.nickname")

MAX_NICKNAME_LENGTH = 32


def build_nickname(party: str, first_name: str, last_name: str) -> str:
    tag = config.PARTY_TAGS.get(party, "BEZP.")
    full_name = f"{first_name} {last_name}".strip()
    nickname = f"[{tag}] {full_name}"

    if len(nickname) <= MAX_NICKNAME_LENGTH:
        return nickname

    prefix = f"[{tag}] "
    available = MAX_NICKNAME_LENGTH - len(prefix)
    return prefix + full_name[:available].rstrip()


async def apply_nickname(member: discord.Member, party: str, first_name: str, last_name: str) -> bool:
    """
    Zwraca True jesli nick zostal ustawiony. Zwraca False (i loguje ostrzezenie)
    jesli bot nie ma uprawnien - np. rola bota jest nizej niz rola docelowego
    czlonka, albo to wlasciciel serwera (Discord nigdy nie pozwala botom
    zmieniac nicku wlasciciela, niezaleznie od uprawnien roli).
    """
    nickname = build_nickname(party, first_name, last_name)

    if member.display_name == nickname:
        return True  # nic do zmiany

    try:
        await member.edit(nick=nickname, reason="Aktualizacja nicku: obywatel/partia")
        return True
    except discord.Forbidden:
        log.warning(
            "Brak uprawnien do zmiany nicku dla %s (rola bota za nisko w hierarchii "
            "albo to wlasciciel serwera - Discord tego nie pozwala zmienic botom).",
            member,
        )
        return False
    except discord.HTTPException:
        log.exception("Blad przy zmianie nicku dla %s", member)
        return False
