"""
cogs/verification.py

Panel weryfikacji: administrator wystawia embed z przyciskiem "Zweryfikuj się".
Kliknięcie otwiera formularz: nazwa Roblox, imię i nazwisko postaci,
rok urodzenia, stan/region zamieszkania. Po poprawnym wypełnieniu bot:
- sprawdza, czy konto Roblox istnieje,
- generuje unikalny SSN na podstawie roku urodzenia,
- zapisuje rekord obywatela w Firebase,
- nadaje role "Zweryfikowany" i "Obywatel".
"""

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
import firebase_client as db
from nickname_utils import apply_nickname
from roblox_api import lookup_roblox_user
from ssn_utils import generate_unique_ssn, reserve_ssn

VERIFY_BUTTON_CUSTOM_ID = "verification:open_modal"


class VerificationModal(discord.ui.Modal, title="Weryfikacja obywatela"):
    roblox_username = discord.ui.TextInput(
        label="Nazwa użytkownika Roblox",
        placeholder="np. JanKowalski123",
        max_length=32,
    )
    first_name = discord.ui.TextInput(
        label="Imię postaci",
        max_length=32,
    )
    last_name = discord.ui.TextInput(
        label="Nazwisko postaci",
        max_length=32,
    )
    birth_year = discord.ui.TextInput(
        label="Rok urodzenia postaci",
        placeholder="np. 1990",
        max_length=4,
    )
    residence = discord.ui.TextInput(
        label="Stan / region zamieszkania",
        placeholder="np. Kalifornia",
        max_length=64,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        birth_year_str = str(self.birth_year.value).strip()
        if not birth_year_str.isdigit() or not (1900 <= int(birth_year_str) <= datetime.now().year):
            await interaction.followup.send(
                "Rok urodzenia musi być liczbą w rozsądnym zakresie (np. 1900–obecny rok).",
                ephemeral=True,
            )
            return
        birth_year = int(birth_year_str)

        roblox_user = await lookup_roblox_user(str(self.roblox_username.value).strip())
        if roblox_user is None:
            await interaction.followup.send(
                "Nie znaleziono takiego użytkownika Roblox. Sprawdź pisownię nazwy i spróbuj ponownie.",
                ephemeral=True,
            )
            return

        existing = await db.get(f"citizens/{interaction.user.id}")
        if existing:
            ssn = existing.get("ssn")
        else:
            ssn = await generate_unique_ssn(birth_year)
            await reserve_ssn(ssn, interaction.user.id)

        record = {
            "discordId": str(interaction.user.id),
            "discordTag": str(interaction.user),
            "robloxUsername": roblox_user["name"],
            "robloxUserId": roblox_user["id"],
            "firstName": str(self.first_name.value).strip(),
            "lastName": str(self.last_name.value).strip(),
            "birthYear": birth_year,
            "residence": str(self.residence.value).strip(),
            "ssn": ssn,
            "party": existing.get("party", "Niezależny") if existing else "Niezależny",
            "degree": existing.get("degree", "Brak") if existing else "Brak",
            "verifiedAt": datetime.now(timezone.utc).isoformat(),
        }

        ok = await db.put(f"citizens/{interaction.user.id}", record)
        if not ok:
            await interaction.followup.send(
                "Wystąpił błąd zapisu danych. Spróbuj ponownie później.",
                ephemeral=True,
            )
            return

        added_roles = []
        guild = interaction.guild
        member = interaction.user
        if guild and isinstance(member, discord.Member):
            role_ids_to_add = [*config.ROLE_VERIFIED_IDS, *config.ROLE_CITIZEN_IDS]
            for role_id in role_ids_to_add:
                role = guild.get_role(role_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Weryfikacja Roblox")
                        added_roles.append(role.name)
                    except discord.Forbidden:
                        pass

            await apply_nickname(member, record["party"], record["firstName"], record["lastName"])

        embed = discord.Embed(
            title="Weryfikacja zakończona pomyślnie",
            color=discord.Color.green(),
            description=(
                f"**Postać:** {record['firstName']} {record['lastName']}\n"
                f"**Konto Roblox:** {record['robloxUsername']}\n"
                f"**Rok urodzenia:** {birth_year}\n"
                f"**Zamieszkanie:** {record['residence']}\n"
                f"**SSN:** {ssn}"
            ),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Zweryfikuj się",
        style=discord.ButtonStyle.blurple,
        custom_id=VERIFY_BUTTON_CUSTOM_ID,
        emoji="🪪",
    )
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerificationModal())


class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Rejestracja trwałego widoku — działa też po restarcie bota,
        # bo custom_id jest stały.
        self.bot.add_view(VerificationView())

    @app_commands.command(name="panel-weryfikacja", description="Wystawia panel weryfikacji Roblox na tym kanale (admin).")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def panel_weryfikacja(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = discord.Embed(
            title="🪪 Weryfikacja obywatela",
            description=(
                "Aby otrzymać rolę **Zweryfikowany** i **Obywatel**, połącz swoje "
                "konto Roblox i podaj dane swojej postaci.\n\n"
                "Kliknij przycisk poniżej, aby rozpocząć."
            ),
            color=discord.Color.blurple(),
        )
        await interaction.channel.send(embed=embed, view=VerificationView())
        await interaction.followup.send("Panel weryfikacji został wystawiony.", ephemeral=True)

    @panel_weryfikacja.error
    async def panel_weryfikacja_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "Nie masz uprawnień do użycia tej komendy.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))
