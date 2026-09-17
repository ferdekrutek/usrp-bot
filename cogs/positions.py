"""
cogs/positions.py

- /stan <rola> <nazwa_stanowiska> - mapuje role Discord na nazwe stanowiska
  pokazywana w /postac. Sama komenda TYLKO rejestruje mapowanie - nadanie
  konkretnej roli konkretnej osobie admin robi normalnie przez Discorda
  (albo przez inna komende bota, jesli taka rola jest np. Senatorem/
  Reprezentantem - to nadaje sie automatycznie po akceptacji podania).

- /mandat-odbierz <uzytkownik> - odbiera aktualny mandat Senatora/
  Reprezentanta: zmienia status jego zaakceptowanego podania na "revoked"
  (zamiast usuwac - zostaje slad w historii) i zdejmuje odpowiednie role.
"""

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
import firebase_client as db
from permissions import is_admin


class PositionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="stan", description="Mapuje role Discord na nazwe stanowiska widoczna w /postac (admin).")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        rola="Rola Discord, ktora ma odpowiadac stanowisku",
        stanowisko="Nazwa stanowiska do wyswietlenia, np. 'Prezydent', 'Sekretarz Stanu'",
    )
    async def stan(self, interaction: discord.Interaction, rola: discord.Role, stanowisko: str):
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Nie masz uprawnień do tej komendy.", ephemeral=True)
            return

        nazwa = stanowisko.strip()
        if not nazwa:
            await interaction.response.send_message("Nazwa stanowiska nie może być pusta.", ephemeral=True)
            return

        await db.put(f"position_roles/{rola.id}", nazwa)

        await interaction.response.send_message(
            f"Rola {rola.mention} będzie teraz wyświetlana w `/postac` jako stanowisko **{nazwa}**.\n"
            f"Pamiętaj, żeby faktycznie nadać tę rolę osobie na Discordzie — ta komenda tylko "
            f"rejestruje, co ta rola oznacza.",
            ephemeral=True,
        )

    @app_commands.command(name="mandat-odbierz", description="Odbiera mandat Senatora/Reprezentanta (admin).")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(uzytkownik="Komu odebrać mandat")
    async def mandat_odbierz(self, interaction: discord.Interaction, uzytkownik: discord.Member):
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Nie masz uprawnień do tej komendy.", ephemeral=True)
            return

        applications = await db.get("applications") or {}
        active = [
            (app_id, application)
            for app_id, application in applications.items()
            if application
            and application.get("discordId") == str(uzytkownik.id)
            and application.get("status") == "accepted"
        ]

        if not active:
            await interaction.response.send_message(
                f"{uzytkownik.mention} nie ma aktualnie żadnego mandatu (Senator/Reprezentant).",
                ephemeral=True,
            )
            return

        revoked_positions = set()
        for app_id, application in active:
            await db.patch(f"applications/{app_id}", {
                "status": "revoked",
                "revokedBy": str(interaction.user),
                "revokedAt": datetime.now(timezone.utc).isoformat(),
            })
            revoked_positions.add(application["position"])

        role_ids_to_remove = []
        if "Senator" in revoked_positions:
            role_ids_to_remove += config.ROLE_SENATOR_IDS
        if "Reprezentant" in revoked_positions:
            role_ids_to_remove += config.ROLE_REPRESENTATIVE_IDS

        removed_roles = []
        for role_id in role_ids_to_remove:
            role = uzytkownik.guild.get_role(role_id)
            if role and role in uzytkownik.roles:
                try:
                    await uzytkownik.remove_roles(role, reason=f"Mandat odebrany przez {interaction.user}")
                    removed_roles.append(role.name)
                except discord.Forbidden:
                    pass

        await interaction.response.send_message(
            f"Odebrano mandat ({', '.join(revoked_positions)}) dla {uzytkownik.mention}.\n"
            f"Role zdjęte: {', '.join(removed_roles) if removed_roles else 'brak (sprawdź hierarchię ról bota)'}.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(PositionsCog(bot))
