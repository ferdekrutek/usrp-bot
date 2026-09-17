"""
cogs/citizen.py

Komenda /postac - pokazuje profil postaci (imie i nazwisko, stopien
naukowy, partia, miejsce zamieszkania, SSN). Mozna wyszukac po
uzytkowniku Discorda ALBO po (fragmencie) numeru SSN.

Wyszukiwanie po SSN dziala na zasadzie "zawiera te cyfry" - nikt nie
pamieta calego numeru, wiec dopasowujemy podciag cyfr. Jesli pasuje
wiecej niz jedna postac, bot pokazuje liste do wyboru (max 25, limit
Discorda dla select menu).

Dodatkowo komendy administracyjne: /postac-edytuj i /postac-usun.
"""

from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
import firebase_client as db
from nickname_utils import apply_nickname
from permissions import is_admin


def _build_profile_embed(citizen: dict, discord_tag: str, member: Optional[discord.Member] = None) -> discord.Embed:
    embed = discord.Embed(
        title=f"🪪 {citizen.get('firstName', '?')} {citizen.get('lastName', '?')}",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Stopień naukowy", value=citizen.get("degree", "Brak"), inline=True)
    embed.add_field(name="Partia", value=citizen.get("party", "Niezależny"), inline=True)
    embed.add_field(name="Miejsce zamieszkania", value=citizen.get("residence", "Nieznane"), inline=True)
    embed.add_field(name="SSN", value=f"`{citizen.get('ssn', 'Brak')}`", inline=True)
    embed.add_field(name="Konto Roblox", value=citizen.get("robloxUsername", "Nieznane"), inline=True)
    embed.set_footer(text=f"Discord: {discord_tag}")
    if member is not None:
        embed.set_thumbnail(url=member.display_avatar.url)
    return embed


class SsnMatchSelect(discord.ui.Select):
    def __init__(self, matches: list[tuple[str, dict]]):
        options = []
        for discord_id, citizen in matches[:25]:
            label = f"{citizen.get('firstName', '?')} {citizen.get('lastName', '?')}"
            description = f"{citizen.get('party', '?')} • SSN: {citizen.get('ssn', '?')}"
            options.append(discord.SelectOption(label=label[:100], description=description[:100], value=discord_id))
        super().__init__(placeholder="Wybierz postać...", options=options)

    async def callback(self, interaction: discord.Interaction):
        discord_id = self.values[0]
        citizen = await db.get(f"citizens/{discord_id}")
        if not citizen:
            await interaction.response.send_message(
                "Nie znaleziono tej postaci (mogła zostać usunięta).", ephemeral=True
            )
            return
        member = interaction.guild.get_member(int(discord_id)) if interaction.guild else None
        discord_tag = citizen.get("discordTag", "Nieznany")
        embed = _build_profile_embed(citizen, discord_tag, member)
        await interaction.response.edit_message(content=None, embed=embed, view=None)


class SsnMatchView(discord.ui.View):
    def __init__(self, matches: list[tuple[str, dict]]):
        super().__init__(timeout=120)
        self.add_item(SsnMatchSelect(matches))


class CitizenCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="postac", description="Pokazuje profil postaci po nicku Discord albo po (fragmencie) SSN.")
    @app_commands.describe(
        uzytkownik="Uzytkownik Discorda, ktorego profil chcesz zobaczyc",
        ssn="Cale lub czesciowe cyfry SSN postaci, np. 4-5678 albo 5678",
    )
    async def postac(
        self,
        interaction: discord.Interaction,
        uzytkownik: Optional[discord.Member] = None,
        ssn: Optional[str] = None,
    ):
        if uzytkownik is None and not ssn:
            await interaction.response.send_message(
                "Podaj albo uzytkownika Discord, albo (fragment) SSN.", ephemeral=True
            )
            return

        if uzytkownik is not None and ssn:
            await interaction.response.send_message(
                "Podaj tylko jedno: uzytkownika ALBO SSN, nie oba naraz.", ephemeral=True
            )
            return

        if uzytkownik is not None:
            await interaction.response.defer(ephemeral=False, thinking=True)
            citizen = await db.get(f"citizens/{uzytkownik.id}")
            if not citizen:
                await interaction.followup.send(
                    f"{uzytkownik.mention} nie jest zweryfikowanym obywatelem.", ephemeral=True
                )
                return
            embed = _build_profile_embed(citizen, str(uzytkownik), uzytkownik)
            await interaction.followup.send(embed=embed)
            return

        # Wyszukiwanie po (fragmencie) SSN
        await interaction.response.defer(ephemeral=True, thinking=True)

        digits_query = "".join(ch for ch in ssn if ch.isdigit())
        if not digits_query:
            await interaction.followup.send("Podaj przynajmniej kilka cyfr SSN.", ephemeral=True)
            return

        citizens = await db.get("citizens") or {}
        matches = []
        for discord_id, citizen in citizens.items():
            if not citizen:
                continue
            stored_digits = "".join(ch for ch in citizen.get("ssn", "") if ch.isdigit())
            if digits_query in stored_digits:
                matches.append((discord_id, citizen))

        if not matches:
            await interaction.followup.send("Nie znaleziono żadnej postaci z takimi cyframi SSN.", ephemeral=True)
            return

        if len(matches) == 1:
            discord_id, citizen = matches[0]
            member = interaction.guild.get_member(int(discord_id)) if interaction.guild else None
            embed = _build_profile_embed(citizen, citizen.get("discordTag", "Nieznany"), member)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        note = ""
        if len(matches) > 25:
            note = f"\n\n_Znaleziono {len(matches)} dopasowań, pokazuję pierwsze 25 — wpisz więcej cyfr, żeby zawęzić wyniki._"

        embed = discord.Embed(
            title="🔎 Znaleziono kilka pasujących postaci",
            description=f"Podane cyfry pasują do **{len(matches)}** rekordów. Wybierz z listy poniżej.{note}",
            color=discord.Color.blurple(),
        )
        await interaction.followup.send(embed=embed, view=SsnMatchView(matches), ephemeral=True)

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

        role_ids_to_remove = [
            config.ROLE_VERIFIED_ID,
            config.ROLE_CITIZEN_ID,
            *config.ROLE_SENATOR_IDS,
            *config.ROLE_REPRESENTATIVE_IDS,
        ]

        removed_roles = []
        for role_id in role_ids_to_remove:
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
