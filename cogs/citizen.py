"""
cogs/citizen.py

Komenda /postac - pokazuje profil postaci (imie i nazwisko, stopien
naukowy, partia, miejsce zamieszkania, SSN). Mozna wyszukac po
uzytkowniku Discorda ALBO po numerze SSN (dokladnie jedno z dwoch).
"""

from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
import firebase_client as db
from nickname_utils import apply_nickname
from permissions import is_admin


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

    @app_commands.command(name="postac-edytuj", description="Poprawia dane postaci obywatela (admin).")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        uzytkownik="Czyje dane edytujesz",
        pole="Które pole zmienić",
        wartosc="Nowa wartość tego pola",
    )
    @app_commands.choices(pole=[
        app_commands.Choice(name="Imię", value="firstName"),
        app_commands.Choice(name="Nazwisko", value="lastName"),
        app_commands.Choice(name="Zamieszkanie", value="residence"),
        app_commands.Choice(name="Rok urodzenia", value="birthYear"),
    ])
    async def postac_edytuj(
        self,
        interaction: discord.Interaction,
        uzytkownik: discord.Member,
        pole: app_commands.Choice[str],
        wartosc: str,
    ):
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Nie masz uprawnień do tej komendy.", ephemeral=True)
            return

        citizen = await db.get(f"citizens/{uzytkownik.id}")
        if not citizen:
            await interaction.response.send_message(
                f"{uzytkownik.mention} nie jest zweryfikowanym obywatelem.", ephemeral=True
            )
            return

        if pole.value == "birthYear":
            value = wartosc.strip()
            if not value.isdigit() or not (1900 <= int(value) <= datetime.now().year):
                await interaction.response.send_message(
                    "Rok urodzenia musi być liczbą w rozsądnym zakresie (np. 1900–obecny rok).",
                    ephemeral=True,
                )
                return
            update = {"birthYear": int(value)}
        else:
            update = {pole.value: wartosc.strip()}

        ok = await db.patch(f"citizens/{uzytkownik.id}", update)
        if not ok:
            await interaction.response.send_message(
                "Wystąpił błąd zapisu danych. Spróbuj ponownie później.", ephemeral=True
            )
            return

        # Jesli zmienilismy imie/nazwisko, od razu odswiez nick (z aktualna partia)
        if pole.value in ("firstName", "lastName"):
            refreshed = await db.get(f"citizens/{uzytkownik.id}")
            if refreshed:
                await apply_nickname(
                    uzytkownik,
                    refreshed.get("party", "Niezależny"),
                    refreshed.get("firstName", ""),
                    refreshed.get("lastName", ""),
                )

        await interaction.response.send_message(
            f"Zaktualizowano pole **{pole.name}** dla {uzytkownik.mention} → `{wartosc.strip()}`.",
            ephemeral=True,
        )

    @app_commands.command(name="postac-usun", description="Usuwa na trwałe rekord obywatela (admin).")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(uzytkownik="Czyj rekord chcesz usunąć")
    async def postac_usun(self, interaction: discord.Interaction, uzytkownik: discord.Member):
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Nie masz uprawnień do tej komendy.", ephemeral=True)
            return

        citizen = await db.get(f"citizens/{uzytkownik.id}")
        if not citizen:
            await interaction.response.send_message(
                f"{uzytkownik.mention} nie ma rekordu obywatela do usunięcia.", ephemeral=True
            )
            return

        await db.delete(f"citizens/{uzytkownik.id}")

        ssn = citizen.get("ssn")
        if ssn:
            await db.delete(f"ssn_index/{ssn.replace('-', '_')}")

        removed_roles = []
        for role_id in (
            config.ROLE_VERIFIED_ID,
            config.ROLE_CITIZEN_ID,
            config.ROLE_SENATOR_ID,
            config.ROLE_REPRESENTATIVE_ID,
        ):
            if role_id:
                role = uzytkownik.guild.get_role(role_id)
                if role and role in uzytkownik.roles:
                    try:
                        await uzytkownik.remove_roles(role, reason=f"Usuniecie rekordu obywatela przez {interaction.user}")
                        removed_roles.append(role.name)
                    except discord.Forbidden:
                        pass

        try:
            await uzytkownik.edit(nick=None, reason="Usuniecie rekordu obywatela")
        except discord.Forbidden:
            pass

        await interaction.response.send_message(
            f"Rekord obywatela {uzytkownik.mention} został usunięty (role zdjęte: "
            f"{', '.join(removed_roles) if removed_roles else 'brak'}).",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(CitizenCog(bot))
