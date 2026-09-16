"""
cogs/elections.py

Prosty przelacznik stanu wyborow, bo gra na Robloxie nie dziala caly czas.
Status trzymany jest w Firebase pod /settings/electionsOpen, wiec gra
(albo dowolna inna integracja) moze go odczytac niezaleznie od bota.

Komendy: /wybory otworz, /wybory zamknij, /wybory status
"""

import discord
from discord import app_commands
from discord.ext import commands

import firebase_client as db
from permissions import is_admin


class ElectionsCog(commands.GroupCog, name="wybory"):
    """Grupa komend /wybory - zarzadzanie stanem wyborow."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="otworz", description="Otwiera wybory (admin).")
    @app_commands.default_permissions(manage_guild=True)
    async def otworz(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Nie masz uprawnien do tej komendy.", ephemeral=True)
            return
        await db.put("settings/electionsOpen", True)
        await interaction.response.send_message("Wybory zostaly otwarte.")

    @app_commands.command(name="zamknij", description="Zamyka wybory (admin).")
    @app_commands.default_permissions(manage_guild=True)
    async def zamknij(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Nie masz uprawnien do tej komendy.", ephemeral=True)
            return
        await db.put("settings/electionsOpen", False)
        await interaction.response.send_message("Wybory zostaly zamkniete.")

    @app_commands.command(name="status", description="Sprawdza, czy wybory sa aktualnie otwarte.")
    async def status(self, interaction: discord.Interaction):
        is_open = await db.get("settings/electionsOpen")
        text = "Wybory sa obecnie otwarte." if is_open else "Wybory sa obecnie zamkniete."
        await interaction.response.send_message(text)


async def setup(bot: commands.Bot):
    await bot.add_cog(ElectionsCog(bot))
