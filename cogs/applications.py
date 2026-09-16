"""
cogs/applications.py

Dwa osobne panele podan:
- /panel-senat  -> jeden przycisk "Aplikuj na Senatora"
- /panel-izba   -> jeden przycisk "Aplikuj na Reprezentanta"

Kliknięcie otwiera formularz (imię, nazwisko, partia, region). Zgłoszenie
trafia do kanału administracji z przyciskami Akceptuj / Odrzuć. Po zlozeniu
podania partia obywatela jest aktualizowana i nick na serwerze zmienia sie
na "[TAG_PARTII] Imie Nazwisko" (np. "[REP.] Jan Kowalski").

Podania i ich status trzymane sa w Firebase pod /applications/{id},
dzieki czemu panel akceptacji odbudowuje sie nawet po restarcie bota.
"""

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
import firebase_client as db
from nickname_utils import apply_nickname
from permissions import is_admin

APPLY_SENATOR_CUSTOM_ID = "applications:apply_senator"
APPLY_REPRESENTATIVE_CUSTOM_ID = "applications:apply_representative"


def _party_is_valid(party: str) -> bool:
    return party.strip().lower() in {p.lower() for p in config.PARTIES}


def _normalize_party(party: str) -> str:
    for p in config.PARTIES:
        if p.lower() == party.strip().lower():
            return p
    return party.strip()


class ApplicationModal(discord.ui.Modal, title="Formularz kandydata"):
    def __init__(self, position: str):
        super().__init__()
        self.position = position

    first_name = discord.ui.TextInput(label="Imię", max_length=32)
    last_name = discord.ui.TextInput(label="Nazwisko", max_length=32)
    party = discord.ui.TextInput(
        label="Przynależność do partii",
        placeholder=", ".join(config.PARTIES),
    )
    region = discord.ui.TextInput(
        label="Region (stan / obszar)",
        placeholder="np. Teksas",
        max_length=64,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        citizen = await db.get(f"citizens/{interaction.user.id}")
        if not citizen:
            await interaction.followup.send(
                "Musisz najpierw przejsc weryfikacje (rola Obywatel), zanim zlozysz podanie.",
                ephemeral=True,
            )
            return

        if not _party_is_valid(str(self.party.value)):
            await interaction.followup.send(
                "Nieprawidlowa partia. Dostepne opcje: " + ", ".join(config.PARTIES),
                ephemeral=True,
            )
            return

        normalized_party = _normalize_party(str(self.party.value))

        application = {
            "discordId": str(interaction.user.id),
            "discordTag": str(interaction.user),
            "position": self.position,
            "firstName": str(self.first_name.value).strip(),
            "lastName": str(self.last_name.value).strip(),
            "party": normalized_party,
            "region": str(self.region.value).strip(),
            "status": "pending",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        app_id = await db.push("applications", application)
        if not app_id:
            await interaction.followup.send(
                "Wystapil blad zapisu podania. Sprobuj ponownie pozniej.", ephemeral=True
            )
            return

        # Zlozenie podania deklaruje partie kandydata "publicznie" - aktualizujemy
        # rekord obywatela i nick na serwerze od razu, a nie dopiero po akceptacji.
        await db.patch(f"citizens/{interaction.user.id}", {"party": normalized_party})
        if isinstance(interaction.user, discord.Member):
            await apply_nickname(
                interaction.user,
                normalized_party,
                citizen.get("firstName", application["firstName"]),
                citizen.get("lastName", application["lastName"]),
            )

        await interaction.followup.send(
            "Twoje podanie zostalo wyslane do administracji. Otrzymasz wiadomosc prywatna z decyzja.",
            ephemeral=True,
        )

        review_channel_id = config.APPLICATIONS_REVIEW_CHANNEL_ID
        if review_channel_id:
            channel = interaction.client.get_channel(review_channel_id)
            if channel:
                embed = _build_review_embed(app_id, application)
                view = AdminReviewView(app_id)
                message = await channel.send(embed=embed, view=view)
                interaction.client.add_view(view, message_id=message.id)


def _build_review_embed(app_id: str, application: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"Nowe podanie — {application['position']}",
        color=discord.Color.orange(),
        description=(
            f"**Kandydat:** {application['firstName']} {application['lastName']}\n"
            f"**Discord:** {application['discordTag']} (<@{application['discordId']}>)\n"
            f"**Partia:** {application['party']}\n"
            f"**Region:** {application['region']}"
        ),
    )
    embed.set_footer(text=f"ID podania: {app_id}")
    return embed


class AdminReviewView(discord.ui.View):
    def __init__(self, app_id: str):
        super().__init__(timeout=None)
        self.app_id = app_id
        self.accept_button.custom_id = f"applications:accept:{app_id}"
        self.reject_button.custom_id = f"applications:reject:{app_id}"

    async def _finalize(self, interaction: discord.Interaction, status: str):
        member = interaction.user
        if not isinstance(member, discord.Member) or not is_admin(member):
            await interaction.response.send_message(
                "Nie masz uprawnien do rozpatrywania podan.", ephemeral=True
            )
            return

        application = await db.get(f"applications/{self.app_id}")
        if not application:
            await interaction.response.send_message("Nie znaleziono tego podania (moglo zostac usuniete).", ephemeral=True)
            return

        if application.get("status") != "pending":
            await interaction.response.send_message("To podanie zostalo juz rozpatrzone.", ephemeral=True)
            return

        await db.patch(f"applications/{self.app_id}", {
            "status": status,
            "reviewedBy": str(member),
            "reviewedAt": datetime.now(timezone.utc).isoformat(),
        })

        if status == "accepted" and interaction.guild:
            role_id = (
                config.ROLE_SENATOR_ID
                if application["position"] == "Senator"
                else config.ROLE_REPRESENTATIVE_ID
            )
            if role_id:
                role = interaction.guild.get_role(role_id)
                target = interaction.guild.get_member(int(application["discordId"]))
                if role and target:
                    try:
                        await target.add_roles(role, reason=f"Podanie zaakceptowane przez {member}")
                    except discord.Forbidden:
                        pass

        decision_pl = "zaakceptowane ✅" if status == "accepted" else "odrzucone ❌"
        for item in self.children:
            item.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green() if status == "accepted" else discord.Color.red()
        embed.add_field(name="Decyzja", value=f"{decision_pl} przez {member.mention}", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

        applicant = interaction.client.get_user(int(application["discordId"]))
        if applicant:
            try:
                await applicant.send(
                    f"Twoje podanie na **{application['position']}** zostalo **{decision_pl}**."
                )
            except discord.Forbidden:
                pass

    @discord.ui.button(label="Akceptuj", style=discord.ButtonStyle.success, custom_id="applications:accept:placeholder")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finalize(interaction, "accepted")

    @discord.ui.button(label="Odrzuć", style=discord.ButtonStyle.danger, custom_id="applications:reject:placeholder")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finalize(interaction, "rejected")


class SenatorApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aplikuj na Senatora",
        style=discord.ButtonStyle.blurple,
        custom_id=APPLY_SENATOR_CUSTOM_ID,
        emoji="🏛️",
    )
    async def apply_senator(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplicationModal("Senator"))


class RepresentativeApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aplikuj na Reprezentanta",
        style=discord.ButtonStyle.blurple,
        custom_id=APPLY_REPRESENTATIVE_CUSTOM_ID,
        emoji="📜",
    )
    async def apply_representative(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplicationModal("Reprezentant"))


class ApplicationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(SenatorApplicationView())
        self.bot.add_view(RepresentativeApplicationView())

    async def cog_load(self):
        # Odbudowuje przyciski Akceptuj/Odrzuc dla wszystkich podan
        # oczekujacych, zeby dzialaly tez po restarcie bota.
        applications = await db.get("applications")
        if not applications:
            return
        for app_id, application in applications.items():
            if application and application.get("status") == "pending":
                self.bot.add_view(AdminReviewView(app_id))

    @app_commands.command(name="panel-senat", description="Wystawia panel podan na Senatora na tym kanale (admin).")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def panel_senat(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = discord.Embed(
            title="🏛️ REKRUTACJA — SENAT",
            description=(
                "Aplikuj na stanowisko Senatora.\n\n"
                "Kliknij przycisk ponizej, wybierz partie i wypelnij formularz. "
                "Administracja rozpatrzy Twoje zgloszenie."
            ),
            color=discord.Color.dark_red(),
        )
        await interaction.channel.send(embed=embed, view=SenatorApplicationView())
        await interaction.followup.send("Panel podan na Senatora zostal wystawiony.", ephemeral=True)

    @app_commands.command(name="panel-izba", description="Wystawia panel podan na Reprezentanta na tym kanale (admin).")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def panel_izba(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = discord.Embed(
            title="📜 REKRUTACJA — IZBA REPREZENTANTÓW",
            description=(
                "Aplikuj na stanowisko czlonka Izby Reprezentantow.\n\n"
                "Kliknij przycisk ponizej, wybierz partie i wypelnij formularz. "
                "Administracja rozpatrzy Twoje zgloszenie."
            ),
            color=discord.Color.dark_blue(),
        )
        await interaction.channel.send(embed=embed, view=RepresentativeApplicationView())
        await interaction.followup.send("Panel podan na Reprezentanta zostal wystawiony.", ephemeral=True)

    @panel_senat.error
    @panel_izba.error
    async def panel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "Nie masz uprawnien do uzycia tej komendy.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(ApplicationsCog(bot))
