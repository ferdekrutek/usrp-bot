"""
cogs/party.py

Komenda /zmien-partie <partia> - pozwala zweryfikowanemu obywatelowi
samodzielnie zmienic przynaleznosc partyjna na jedna z list w config.py.
Po zmianie aktualizuje tez tag partii w nicku na serwerze.
"""

import discord
from discord import app_commands
from discord.ext import commands

import config
import firebase_client as db
from nickname_utils import apply_nickname


class PartyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="zmien-partie", description="Zmienia twoja przynaleznosc partyjna.")
    @app_commands.choices(
        partia=[app_commands.Choice(name=p, value=p) for p in config.PARTIES]
    )
    async def zmien_partie(self, interaction: discord.Interaction, partia: app_commands.Choice[str]):
        citizen = await db.get(f"citizens/{interaction.user.id}")
        if not citizen:
            await interaction.response.send_message(
                "Musisz najpierw przejsc weryfikacje, zanim zmienisz partie.", ephemeral=True
            )
            return

        await db.patch(f"citizens/{interaction.user.id}", {"party": partia.value})

        if isinstance(interaction.user, discord.Member):
            await apply_nickname(
                interaction.user,
                partia.value,
                citizen.get("firstName", ""),
                citizen.get("lastName", ""),
            )

        await interaction.response.send_message(
            f"Twoja przynaleznosc partyjna zostala zmieniona na **{partia.value}**.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(PartyCog(bot))
