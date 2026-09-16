"""
cogs/citizen.py

Komenda /postac - pokazuje profil postaci (imie i nazwisko, stopien
naukowy, partia, miejsce zamieszkania, SSN). Mozna wyszukac po
uzytkowniku Discorda ALBO po numerze SSN (dokladnie jedno z dwoch).
"""

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import firebase_client as db


def _normalize_ssn(raw: str) -> str:
    """Akceptuje SSN z myslnikami, bez myslnikow, ze spacjami itp."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 9:
        return f"{digits[0:3]}-{digits[3:5]}-{digits[5:9]}"
    return raw.strip()


def _build_profile_embed(citizen: dict, discord_tag: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"Profil postaci — {citizen.get('firstName')} {citizen.get('lastName')}",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Stopień naukowy", value=citizen.get("degree", "Brak"), inline=True)
    embed.add_field(name="Partia", value=citizen.get("party", "Niezależny"), inline=True)
    embed.add_field(name="Miejsce zamieszkania", value=citizen.get("residence", "Nieznane"), inline=True)
    embed.add_field(name="SSN", value=citizen.get("ssn", "Brak"), inline=True)
    embed.add_field(name="Konto Roblox", value=citizen.get("robloxUsername", "Nieznane"), inline=True)
    embed.set_footer(text=f"Discord: {discord_tag}")
    return embed


class CitizenCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="postac", description="Pokazuje profil postaci po nicku Discord albo po SSN.")
    @app_commands.describe(
        uzytkownik="Uzytkownik Discorda, ktorego profil chcesz zobaczyc",
        ssn="Numer SSN postaci, np. 912-34-5678",
    )
    async def postac(
        self,
        interaction: discord.Interaction,
        uzytkownik: Optional[discord.Member] = None,
        ssn: Optional[str] = None,
    ):
        if uzytkownik is None and not ssn:
            await interaction.response.send_message(
                "Podaj albo uzytkownika Discord, albo SSN.", ephemeral=True
            )
            return

        if uzytkownik is not None and ssn:
            await interaction.response.send_message(
                "Podaj tylko jedno: uzytkownika ALBO SSN, nie oba naraz.", ephemeral=True
            )
            return

        if uzytkownik is not None:
            citizen = await db.get(f"citizens/{uzytkownik.id}")
            if not citizen:
                await interaction.response.send_message(
                    f"{uzytkownik.mention} nie jest zweryfikowanym obywatelem.", ephemeral=True
                )
                return
            discord_tag = str(uzytkownik)
        else:
            normalized_ssn = _normalize_ssn(ssn)
            discord_id = await db.get(f"ssn_index/{normalized_ssn.replace('-', '_')}")
            if not discord_id:
                await interaction.response.send_message(
                    "Nie znaleziono postaci o takim SSN.", ephemeral=True
                )
                return
            citizen = await db.get(f"citizens/{discord_id}")
            if not citizen:
                await interaction.response.send_message(
                    "Nie znaleziono postaci o takim SSN.", ephemeral=True
                )
                return
            discord_tag = citizen.get("discordTag", "Nieznany")

        await interaction.response.send_message(embed=_build_profile_embed(citizen, discord_tag))


async def setup(bot: commands.Bot):
    await bot.add_cog(CitizenCog(bot))
