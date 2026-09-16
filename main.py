"""
main.py

Punkt startowy bota. Laduje wszystkie cogi z katalogu cogs/, synchronizuje
komendy slash i uruchamia klienta Discorda.
"""

import asyncio
import logging

import discord
from discord.ext import commands

import config
from keep_alive import run_keep_alive

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("obywatel-bot")

EXTENSIONS = [
    "cogs.verification",
    "cogs.applications",
    "cogs.elections",
    "cogs.degrees",
    "cogs.citizen",
    "cogs.party",
]

intents = discord.Intents.default()
intents.members = True  # wymagane do nadawania rol i odczytu czlonkow


class ObywatelBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
                log.info("Zaladowano rozszerzenie: %s", extension)
            except Exception:
                log.exception("Nie udalo sie zaladowac rozszerzenia: %s", extension)

        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Zsynchronizowano %d komend na serwerze testowym.", len(synced))
        else:
            synced = await self.tree.sync()
            log.info("Zsynchronizowano %d komend globalnie (propagacja moze potrwac do godziny).", len(synced))


    async def on_ready(self):
        log.info("Zalogowano jako %s (ID: %s)", self.user, self.user.id)


async def run_forever():
    """
    Uruchamia bota z reczna obsluga bledu 429 (blokada Cloudflare).

    Darmowy plan Render wysyla ruch z dzielonej puli adresow IP. Jesli inny
    uzytkownik tej puli zbombardowal API Discorda, Cloudflare blokuje CALY
    adres na jakis czas - to nie ma nic wspolnego z Twoim kodem ani tokenem.
    Kazda kolejna proba logowania w trakcie takiej blokady przedluza jej
    czas trwania, wiec zamiast krotkiego, agresywnego retry (i pozwolenia
    Renderowi restartowac caly proces) czekamy dlugo i z rosnacym opoznieniem.
    """
    backoff_seconds = 60
    max_backoff_seconds = 1800  # 30 minut

    while True:
        # Nowa instancja przy kazdej probie: discord.py zamyka wewnetrzna
        # sesje HTTP po nieudanym/przerwanym polaczeniu i nie da sie jej
        # odtworzyc na tym samym obiekcie (RuntimeError: Session is closed).
        bot = ObywatelBot()
        try:
            async with bot:
                await bot.start(config.DISCORD_TOKEN)
            break  # bot.start() zakonczyl sie normalnie - koniec petli
        except discord.HTTPException as error:
            if error.status == 429:
                log.warning(
                    "Discord/Cloudflare zwrocily 429 (prawdopodobnie tymczasowa "
                    "blokada dzielonego IP Render). Czekam %ss przed kolejna proba.",
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)
                continue
            raise
        except discord.LoginFailure:
            log.error("Nieprawidlowy DISCORD_TOKEN - sprawdz zmienna srodowiskowa w Render.")
            raise


def main():
    if not config.DISCORD_TOKEN:
        raise RuntimeError("Brak DISCORD_TOKEN w zmiennych srodowiskowych.")
    if not config.FIREBASE_URL:
        raise RuntimeError("Brak FIREBASE_URL w zmiennych srodowiskowych.")

    run_keep_alive()
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
