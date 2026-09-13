"""
cogs/degrees.py

Komenda /stopien nadaj <uzytkownik> <stopien> - nadaje stopien naukowy
zweryfikowanemu obywatelowi. Liste stopni edytujesz w config.py (DEGREES).
"""

import discord
from discord import app_commands
from discord.ext import commands

import config
import firebase_client as db
from permissions import is_admin


class DegreesCog(commands.GroupCog, name="stopien"):
    """Grupa komend /stopien - zarzadzanie stopniami naukowymi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="nadaj", description="Nadaje stopien naukowy obywatelowi (admin).")
    @app_commands.choices(
        stopien=[app_commands.Choice(name=d, value=d) for d in config.DEGREES]
    )
    async def nadaj(
        self,
        interaction: discord.Interaction,
        uzytkownik: discord.Member,
        stopien: app_commands.Choice[str],
    ):
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Nie masz uprawnien do tej komendy.", ephemeral=True)
            return

        citizen = await db.get(f"citizens/{uzytkownik.id}")
        if not citizen:
            await interaction.response.send_message(
                f"{uzytkownik.mention} nie jest zweryfikowanym obywatelem.", ephemeral=True
            )
            return

        await db.patch(f"citizens/{uzytkownik.id}", {"degree": stopien.value})
        await interaction.response.send_message(
            f"Nadano stopien **{stopien.value}** dla {uzytkownik.mention}."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(DegreesCog(bot))
