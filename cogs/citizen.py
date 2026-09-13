"""
cogs/citizen.py

Komenda /obywatel <uzytkownik> - pokazuje imie i nazwisko, stopien
naukowy, przynaleznosc do partii, miejsce zamieszkania i SSN.
"""

import discord
from discord import app_commands
from discord.ext import commands

import firebase_client as db


class CitizenCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="obywatel", description="Pokazuje profil obywatela.")
    @app_commands.describe(uzytkownik="Uzytkownik Discorda, ktorego profil chcesz zobaczyc")
    async def obywatel(self, interaction: discord.Interaction, uzytkownik: discord.Member):
        citizen = await db.get(f"citizens/{uzytkownik.id}")
        if not citizen:
            await interaction.response.send_message(
                f"{uzytkownik.mention} nie jest zweryfikowanym obywatelem.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"Profil obywatela — {citizen.get('firstName')} {citizen.get('lastName')}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Stopien naukowy", value=citizen.get("degree", "Brak"), inline=True)
        embed.add_field(name="Partia", value=citizen.get("party", "Niezalezny"), inline=True)
        embed.add_field(name="Miejsce zamieszkania", value=citizen.get("residence", "Nieznane"), inline=True)
        embed.add_field(name="SSN", value=citizen.get("ssn", "Brak"), inline=True)
        embed.add_field(name="Konto Roblox", value=citizen.get("robloxUsername", "Nieznane"), inline=True)
        embed.set_footer(text=f"Discord: {uzytkownik}")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CitizenCog(bot))
