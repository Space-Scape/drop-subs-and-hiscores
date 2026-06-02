import asyncio
import json
import os
from pathlib import Path
import discord
import gspread
from discord import app_commands
from discord.ext import commands, tasks
from oauth2client.service_account import ServiceAccountCredentials


DATA_FILE = Path(__file__).with_name("rations.json")
RATIONS_SHEET_ID = os.getenv(
    "RATIONS_SHEET_ID",
    "16FU6Cn3D65CbL1sC2gU8AjUFJWgFxFo9Wa76S3FLzIc",
)
RATIONS_SHEET_HEADER = ["Discord_Name", "Discord_ID", "Total"]
NAME_HEADERS = {"discordname", "discordusername", "name", "username"}
USER_ID_HEADERS = {"discordid", "id", "userid"}
TOTAL_HEADERS = {"ration", "rations", "rationsnumber", "total"}


def load_local_rations() -> dict[str, dict[str, object]]:
    if not DATA_FILE.exists():
        return {}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def write_sheet_rations(
    worksheet: gspread.Worksheet,
    rations: dict[str, dict[str, object]],
) -> None:
    rows = [
        [entry["name"], user_id, int(entry["total"])]
        for user_id, entry in sorted(rations.items())
    ]
    values = [RATIONS_SHEET_HEADER, *rows]
    worksheet.update(
        values=values,
        range_name=f"A1:C{len(values)}",
    )

    first_unused_row = len(values) + 1
    if worksheet.row_count >= first_unused_row:
        worksheet.batch_clear([f"A{first_unused_row}:C{worksheet.row_count}"])


def load_sheet_rations(worksheet: gspread.Worksheet) -> dict[str, dict[str, object]]:
    values = worksheet.get_all_values()
    if not values:
        write_sheet_rations(worksheet, {})
        return {}

    headers = values[0][:3]
    normalized_headers = [
        "".join(character for character in header.lower() if character.isalnum())
        for header in headers
    ]
    if (
        len(normalized_headers) == 3
        and normalized_headers[0] in NAME_HEADERS
        and normalized_headers[1] in USER_ID_HEADERS
        and normalized_headers[2] in TOTAL_HEADERS
    ):
        rows = values[1:]
        name_index, user_id_index = 0, 1
        needs_normalization = headers != RATIONS_SHEET_HEADER
    elif (
        len(normalized_headers) == 3
        and normalized_headers[0] in USER_ID_HEADERS
        and normalized_headers[1] in NAME_HEADERS
        and normalized_headers[2] in TOTAL_HEADERS
    ):
        rows = values[1:]
        name_index, user_id_index = 1, 0
        needs_normalization = True
    elif len(values[0]) >= 3 and values[0][1].strip().isdigit():
        rows = values
        name_index, user_id_index = 0, 1
        needs_normalization = True
    else:
        raise RuntimeError(
            f"Rations worksheet columns must be {RATIONS_SHEET_HEADER}."
        )

    rations = {}
    for row in rows:
        user_id = row[user_id_index].strip() if len(row) > user_id_index else ""
        if not user_id:
            continue

        name = row[name_index].strip() if len(row) > name_index else user_id
        try:
            total = max(0, int(row[2])) if len(row) > 2 else 0
        except ValueError:
            print(f"Skipping invalid ration total for Discord ID {user_id}.")
            continue

        rations[user_id] = {"name": name or user_id, "total": total}

    if needs_normalization:
        write_sheet_rations(worksheet, rations)

    return rations


def ration_emojis(total: int) -> str:
    bowls, rice_balls = divmod(total, 5)
    return ("🍚" * bowls) + ("🍙" * rice_balls)


def format_ration_line(name: object, total: int) -> str:
    display = ration_emojis(total) or "No rations"
    warning = " (risk of starvation)" if total in (1, 2) else ""
    return f"{name}: {display}{warning}"


class RationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rations_sheet = None
        self.rations = {}
        self.rations_lock = asyncio.Lock()

        try:
            self.initialize_rations_sheet()
            print("Rations Cog: Google Sheets initialized successfully.")
        except Exception as error:
            print(f"CRITICAL ERROR initializing RationsCog GSheets: {error}")

    def initialize_rations_sheet(self) -> None:
        if not RATIONS_SHEET_ID:
            raise RuntimeError("Set a non-empty RATIONS_SHEET_ID before loading the cog.")

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials_dict = {
            "type": os.getenv("GOOGLE_TYPE"),
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
            "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv(
                "GOOGLE_AUTH_PROVIDER_X509_CERT_URL"
            ),
            "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN"),
        }
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            credentials_dict,
            scope,
        )
        sheet_client = gspread.authorize(credentials)
        google_sheet = sheet_client.open_by_key(RATIONS_SHEET_ID)
        self.rations_sheet = google_sheet.sheet1

        self.rations = load_sheet_rations(self.rations_sheet)
        local_rations = load_local_rations()
        if not self.rations and local_rations:
            self.rations = local_rations
            self.save_rations()
            print("Rations Cog: Imported local rations.json into Google Sheets.")

    def save_rations(self) -> None:
        if self.rations_sheet is None:
            raise RuntimeError("Rations worksheet is unavailable.")

        write_sheet_rations(self.rations_sheet, self.rations)

    def get_entry(self, member: discord.Member) -> dict[str, object]:
        user_id = str(member.id)
        entry = self.rations.setdefault(
            user_id,
            {"name": member.display_name, "total": 0},
        )
        entry["name"] = member.display_name
        return entry

    async def storage_is_available(self, interaction: discord.Interaction) -> bool:
        if self.rations_sheet is not None:
            return True

        await interaction.response.send_message(
            "Rations storage is unavailable. Please contact an admin.",
            ephemeral=True,
        )
        return False

    def find_member(self, user_id: str) -> discord.Member | None:
        try:
            numeric_user_id = int(user_id)
        except ValueError:
            return None

        for guild in self.bot.guilds:
            member = guild.get_member(numeric_user_id)
            if member is not None:
                return member

        return None

    async def sync_tracked_member_name(self, member: discord.Member) -> None:
        if self.rations_sheet is None:
            return

        async with self.rations_lock:
            entry = self.rations.get(str(member.id))
            if entry is None or entry["name"] == member.display_name:
                return

            previous_name = entry["name"]
            entry["name"] = member.display_name
            try:
                self.save_rations()
            except Exception as error:
                entry["name"] = previous_name
                print(f"Failed to update ration username for {member.id}: {error}")

    async def refresh_member_names_once(self) -> None:
        if self.rations_sheet is None:
            return

        async with self.rations_lock:
            self.rations = load_sheet_rations(self.rations_sheet)
            names_changed = False
            for user_id, entry in self.rations.items():
                member = self.find_member(user_id)
                if member is not None and entry["name"] != member.display_name:
                    entry["name"] = member.display_name
                    names_changed = True

            if names_changed:
                self.save_rations()

    @tasks.loop(hours=3)
    async def refresh_member_names(self) -> None:
        try:
            await self.refresh_member_names_once()
        except Exception as error:
            print(f"Failed to refresh ration usernames: {error}")

    @refresh_member_names.before_loop
    async def before_refresh_member_names(self) -> None:
        await self.bot.wait_until_ready()

    async def cog_load(self) -> None:
        if not self.refresh_member_names.is_running():
            self.refresh_member_names.start()

    def cog_unload(self) -> None:
        self.refresh_member_names.cancel()

    @commands.Cog.listener()
    async def on_member_update(
        self,
        before: discord.Member,
        after: discord.Member,
    ) -> None:
        if before.display_name != after.display_name:
            await self.sync_tracked_member_name(after)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User) -> None:
        if before.name == after.name and before.global_name == after.global_name:
            return

        member = self.find_member(str(after.id))
        if member is not None:
            await self.sync_tracked_member_name(member)

    @app_commands.command(name="addration", description="Add one ration to a person.")
    @app_commands.describe(username="The person receiving a ration")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_ration(
        self,
        interaction: discord.Interaction,
        username: discord.Member,
    ) -> None:
        if not await self.storage_is_available(interaction):
            return

        async with self.rations_lock:
            entry = self.get_entry(username)
            previous_total = int(entry["total"])
            entry["total"] = previous_total + 1
            try:
                self.save_rations()
            except Exception:
                entry["total"] = previous_total
                raise

        await interaction.response.send_message(
            format_ration_line(username.display_name, int(entry["total"])),
            ephemeral=True,
        )

    @app_commands.command(name="removeration", description="Remove one ration from a person.")
    @app_commands.describe(username="The person losing a ration")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_ration(
        self,
        interaction: discord.Interaction,
        username: discord.Member,
    ) -> None:
        if not await self.storage_is_available(interaction):
            return

        async with self.rations_lock:
            entry = self.get_entry(username)
            total = int(entry["total"])

            if total == 0:
                await interaction.response.send_message(
                    f"{username.display_name} has no rations to remove.",
                    ephemeral=True,
                )
                return

            entry["total"] = total - 1
            try:
                self.save_rations()
            except Exception:
                entry["total"] = total
                raise

        await interaction.response.send_message(
            format_ration_line(username.display_name, int(entry["total"])),
            ephemeral=True,
        )

    @app_commands.command(name="rations", description="Show everyone's rations.")
    async def show_rations(self, interaction: discord.Interaction) -> None:
        if not await self.storage_is_available(interaction):
            return

        ranked_entries = sorted(
            self.rations.values(),
            key=lambda entry: (-int(entry["total"]), str(entry["name"]).lower()),
        )
        lines = [
            format_ration_line(entry["name"], int(entry["total"]))
            for entry in ranked_entries
            if int(entry["total"]) > 0
        ]
        leaderboard = "\n".join(lines) if lines else "Nobody has any rations yet."

        await interaction.response.send_message(
            f"{leaderboard}\n\nGlory to the Supreme Leader"
        )

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "Only admins can change rations."
        else:
            message = "Something went wrong while updating rations."
            print(f"Rations command error: {error}")

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RationsCog(bot))
