"""
cogs/congress.py

Komenda /kongres - publiczna lista aktualnego skladu Senatu i Izby
Reprezentantow, budowana z podan o statusie "accepted" w Firebase.

Uwaga na przyszlosc: to prosta lista wszystkich zaakceptowanych podan,
bez pojecia kadencji ani zwalniania miejsca. Jesli kiedys dodamy
kadencje/dymisje, ta komenda bedzie musiala filtrowac tylko "aktywnych"
urzednikow, nie wszystkie zaakceptowane podania w historii.
"""

import discord
from discord import app_commands
from discord.ext import commands

import firebase_client as db

MAX_FIELD_LENGTH = 1000  # bezpieczny margines ponizej limitu Discorda (1024)


def _format_seats(entries: list[str]) -> str:
    if not entries:
        return "Brak obsadzonych miejsc."

    lines = []
    total_length = 0
    for i, entry in enumerate(entries):
        added_length = len(entry) + 1  # +1 na znak nowej linii
        if total_length + added_length > MAX_FIELD_LENGTH:
            remaining = len(entries) - i
            lines.append(f"... i {remaining} więcej")
            break
        lines.append(entry)
        total_length += added_length

    return "\n".join(lines)


class CongressCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kongres", description="Pokazuje aktualny skład Senatu i Izby Reprezentantów.")
    async def kongres(self, interaction: discord.Interaction):
        applications = await db.get("applications") or {}

        senators = []
        representatives = []

        for application in applications.values():
            if not application or application.get("status") != "accepted":
                continue

            entry = (
                f"**{application.get('firstName', '?')} {application.get('lastName', '?')}** "
                f"({application.get('party', '?')}) — {application.get('region', '?')}"
            )

            if application.get("position") == "Senator":
                senators.append(entry)
            else:
                representatives.append(entry)

        embed = discord.Embed(
            title="🏛️ Kongres Stanów Zjednoczonych",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name=f"Senat ({len(senators)})",
            value=_format_seats(senators),
            inline=False,
        )
        embed.add_field(
            name=f"Izba Reprezentantów ({len(representatives)})",
            value=_format_seats(representatives),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CongressCog(bot))
