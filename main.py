"""
main.py

Punkt startowy bota. Laduje wszystkie cogi z katalogu cogs/, synchronizuje
komendy slash i uruchamia klienta Discorda.
"""

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


bot = ObywatelBot()


@bot.event
async def on_ready():
    log.info("Zalogowano jako %s (ID: %s)", bot.user, bot.user.id)


def main():
    if not config.DISCORD_TOKEN:
        raise RuntimeError("Brak DISCORD_TOKEN w zmiennych srodowiskowych.")
    if not config.FIREBASE_URL:
        raise RuntimeError("Brak FIREBASE_URL w zmiennych srodowiskowych.")

    run_keep_alive()
    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
