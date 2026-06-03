import asyncio
import json
import os
import random
import traceback
from datetime import datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
import gspread
from discord import app_commands
from discord.ext import commands, tasks
from oauth2client.service_account import ServiceAccountCredentials


DATA_FILE = Path(__file__).with_name("rations.json")
DEFAULT_RATIONS_SHEET_ID = "16FU6Cn3D65CbL1sC2gU8AjUFJWgFxFo9Wa76S3FLzIc"
RATIONS_SHEET_ID = os.getenv("RATIONS_SHEET_ID") or DEFAULT_RATIONS_SHEET_ID
RATIONS_SHEET_TAB_NAME = "Rations"
RATIONS_SHEET_HEADER = [
    "Discord_Name",
    "Discord_ID",
    "Total",
    "Steals",
    "Labor_Camp_Release",
    "Dead",
]
NAME_HEADERS = {"discordname", "discordusername", "name", "username"}
USER_ID_HEADERS = {"discordid", "id", "userid"}
TOTAL_HEADERS = {"ration", "rations", "rationsnumber", "total"}
STEAL_HEADERS = {"steal", "steals", "cansteal", "dailysteal"}
LABOR_RELEASE_HEADERS = {
    "laborcamprelease",
    "laborrelease",
    "laborcamp",
    "release",
    "releasedat",
}
DEAD_HEADERS = {"dead", "died"}
try:
    CST = ZoneInfo("America/Chicago")
except Exception:
    CST = timezone(timedelta(hours=-6))
STEAL_AVAILABLE = 0
STEAL_USED = 1
DEFAULT_STEALS = STEAL_AVAILABLE
LABOR_PAYOUT = 2
CAUGHT_BASE_PERCENT = 15
CAUGHT_PERCENT_PER_RATION = 5
CAUGHT_MAX_PERCENT = 80


def load_local_rations() -> dict[str, dict[str, object]]:
    if not DATA_FILE.exists():
        return {}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def normalize_header(header: object) -> str:
    return "".join(character for character in str(header).lower() if character.isalnum())


def find_header_index(headers: list[str], accepted_headers: set[str]) -> int | None:
    for index, header in enumerate(headers):
        if header in accepted_headers:
            return index
    return None


def parse_non_negative_int(value: object, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def parse_flag(value: object, default: int = 0) -> int:
    if value in (None, ""):
        return default

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return 1
    if normalized in {"0", "false", "no", "n"}:
        return 0
    return default


def normalize_entry(entry: dict[str, object]) -> dict[str, object]:
    entry["name"] = str(entry.get("name") or "Unknown")
    entry["total"] = parse_non_negative_int(entry.get("total"))
    entry["steals"] = parse_flag(entry.get("steals"), DEFAULT_STEALS)
    entry["labor_release"] = str(entry.get("labor_release") or "")
    entry["dead"] = parse_flag(entry.get("dead"), 0)
    return entry


def parse_labor_release(value: object) -> datetime | None:
    if not value:
        return None

    try:
        release_at = datetime.fromisoformat(str(value))
    except ValueError:
        return None

    if release_at.tzinfo is None:
        return release_at.replace(tzinfo=CST)
    return release_at.astimezone(CST)


def write_sheet_rations(
    worksheet: gspread.Worksheet,
    rations: dict[str, dict[str, object]],
) -> None:
    rows = [
        [
            normalize_entry(entry)["name"],
            user_id,
            int(entry["total"]),
            int(entry["steals"]),
            entry["labor_release"],
            int(entry["dead"]),
        ]
        for user_id, entry in sorted(rations.items())
    ]
    values = [RATIONS_SHEET_HEADER, *rows]
    worksheet.update(
        values=values,
        range_name=f"A1:F{len(values)}",
    )

    first_unused_row = len(values) + 1
    if worksheet.row_count >= first_unused_row:
        worksheet.batch_clear([f"A{first_unused_row}:F{worksheet.row_count}"])


def load_sheet_rations(worksheet: gspread.Worksheet) -> dict[str, dict[str, object]]:
    values = worksheet.get_all_values()
    if not values:
        write_sheet_rations(worksheet, {})
        return {}

    first_row = values[0]
    normalized_headers = [normalize_header(header) for header in first_row]
    if len(first_row) >= 3 and len(first_row) > 1 and str(first_row[1]).strip().isdigit():
        rows = values
        name_index = 0
        user_id_index = 1
        total_index = 2
        steals_index = 3
        labor_release_index = 4
        dead_index = 5
        needs_normalization = True
    elif (
        find_header_index(normalized_headers, NAME_HEADERS) is not None
        and find_header_index(normalized_headers, USER_ID_HEADERS) is not None
        and find_header_index(normalized_headers, TOTAL_HEADERS) is not None
    ):
        rows = values[1:]
        name_index = find_header_index(normalized_headers, NAME_HEADERS)
        user_id_index = find_header_index(normalized_headers, USER_ID_HEADERS)
        total_index = find_header_index(normalized_headers, TOTAL_HEADERS)
        steals_index = find_header_index(normalized_headers, STEAL_HEADERS)
        labor_release_index = find_header_index(
            normalized_headers,
            LABOR_RELEASE_HEADERS,
        )
        dead_index = find_header_index(normalized_headers, DEAD_HEADERS)
        needs_normalization = first_row[: len(RATIONS_SHEET_HEADER)] != RATIONS_SHEET_HEADER
    elif len(values[0]) >= 3 and values[0][1].strip().isdigit():
        rows = values
        name_index, user_id_index = 0, 1
        total_index = 2
        steals_index = 3
        labor_release_index = 4
        dead_index = 5
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
        total = (
            parse_non_negative_int(row[total_index])
            if total_index is not None and len(row) > total_index
            else 0
        )
        if total_index is not None and len(row) > total_index and str(row[total_index]).strip() and not str(row[total_index]).strip().isdigit():
            print(f"Skipping invalid ration total for Discord ID {user_id}.")
            continue

        steals = (
            parse_flag(row[steals_index], DEFAULT_STEALS)
            if steals_index is not None and len(row) > steals_index
            else DEFAULT_STEALS
        )
        labor_release = (
            str(row[labor_release_index]).strip()
            if labor_release_index is not None and len(row) > labor_release_index
            else ""
        )
        dead = (
            parse_flag(row[dead_index], 0)
            if dead_index is not None and len(row) > dead_index
            else 0
        )

        rations[user_id] = normalize_entry(
            {
                "name": name or user_id,
                "total": total,
                "steals": steals,
                "labor_release": labor_release,
                "dead": dead,
            }
        )

    if needs_normalization:
        write_sheet_rations(worksheet, rations)

    return rations


def ration_emojis(total: int) -> str:
    bowls, rice_balls = divmod(total, 5)
    return ("🍚" * bowls) + ("🍙" * rice_balls)


def current_cst_time() -> datetime:
    return datetime.now(CST)


def next_labor_release(now: datetime | None = None) -> datetime:
    now = now or current_cst_time()
    noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if now < noon:
        return noon

    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def next_noon(now: datetime | None = None) -> datetime:
    now = now or current_cst_time()
    noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if now < noon:
        return noon
    return noon + timedelta(days=1)


def next_steal_gain_time(entry: dict[str, object], now: datetime | None = None) -> datetime | None:
    now = now or current_cst_time()
    if is_dead(entry):
        return None

    release_at = parse_labor_release(entry.get("labor_release"))
    if release_at is not None and release_at > now:
        release_at = release_at.astimezone(CST)
        if release_at.hour == 12:
            return release_at
        return release_at.replace(hour=12, minute=0, second=0, microsecond=0)

    return next_noon(now)


def format_release_time(release_at: datetime) -> str:
    return release_at.strftime("%m/%d %I:%M %p")


def is_dead(entry: dict[str, object]) -> bool:
    return parse_flag(entry.get("dead"), 0) == 1


def is_in_labor(entry: dict[str, object], now: datetime | None = None) -> bool:
    release_at = parse_labor_release(entry.get("labor_release"))
    return release_at is not None and release_at > (now or current_cst_time())


def caught_chance_percent(total: int) -> int:
    return min(
        CAUGHT_MAX_PERCENT,
        CAUGHT_BASE_PERCENT + (max(0, total) * CAUGHT_PERCENT_PER_RATION),
    )


def send_to_labor(entry: dict[str, object], now: datetime | None = None) -> datetime:
    release_at = next_labor_release(now)
    entry["labor_release"] = release_at.isoformat(timespec="minutes")
    entry["steals"] = STEAL_USED
    return release_at


def format_ration_line(
    name: object,
    total: int,
    entry: dict[str, object] | None = None,
    now: datetime | None = None,
) -> str:
    entry = entry or {}
    display = ration_emojis(total) or "No rations"
    warning = " (risk of starvation)" if total in (1, 2) else ""
    if is_dead(entry):
        return f"{name}: ☠️ died in the labor camp"

    return f"{name}: {display}{warning}"


def format_labor_line(
    name: object,
    total: int,
    entry: dict[str, object],
    now: datetime | None = None,
) -> str:
    if is_dead(entry):
        return f"☠️ {name} - died in the labor camp."

    release_at = parse_labor_release(entry.get("labor_release"))
    release_text = (
        f"until {format_release_time(release_at)}"
        if release_at is not None
        else "release pending"
    )
    return f"⛏️ {name} - sentenced to hard labor {release_text}."


def can_steal(entry: dict[str, object], now: datetime | None = None) -> bool:
    return (
        not is_dead(entry)
        and not is_in_labor(entry, now)
        and parse_flag(entry.get("steals"), DEFAULT_STEALS) == STEAL_AVAILABLE
    )


def can_be_stolen_from(
    entry: dict[str, object],
    user_id: str,
    thief_id: str,
    now: datetime,
) -> bool:
    return (
        user_id != thief_id
        and not is_dead(entry)
        and not is_in_labor(entry, now)
        and int(entry["total"]) > 0
    )


def steal_status_message(entry: dict[str, object] | None, now: datetime | None = None) -> str:
    if entry is None:
        return "Your daily steal is available."

    if is_dead(entry):
        return "You died in the labor camp."

    release_at = parse_labor_release(entry.get("labor_release"))
    if release_at is not None and release_at > (now or current_cst_time()):
        return f"You are in the labor camp until {format_release_time(release_at)}."

    if parse_flag(entry.get("steals"), DEFAULT_STEALS) == STEAL_AVAILABLE:
        return "Your daily steal is available."

    return "You already used your steal today. It resets at 12:00 PM."


class RationTarget:
    def __init__(self, user_id: str, display_name: str):
        self.id = int(user_id)
        self.display_name = display_name
        self.bot = False


class StealTargetSelect(discord.ui.Select):
    def __init__(
        self,
        cog: "RationsCog",
        thief_id: int,
        options: list[discord.SelectOption],
    ):
        super().__init__(
            placeholder="Choose someone to steal from...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.cog = cog
        self.thief_id = thief_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.thief_id:
            await interaction.response.send_message(
                "This steal menu is not yours.",
                ephemeral=True,
            )
            return

        message = await self.cog.resolve_steal_selection(
            interaction,
            self.values[0],
        )
        self.disabled = True
        if self.view is not None:
            for item in self.view.children:
                item.disabled = True

        await interaction.response.send_message(message)

        if interaction.message is not None:
            try:
                await interaction.message.edit(view=self.view)
            except discord.HTTPException:
                pass


class StealTargetView(discord.ui.View):
    def __init__(
        self,
        cog: "RationsCog",
        thief_id: int,
        options: list[discord.SelectOption],
    ):
        super().__init__(timeout=300)
        self.add_item(StealTargetSelect(cog, thief_id, options))


class RationsView(discord.ui.View):
    def __init__(self, cog: "RationsCog"):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="Steal", style=discord.ButtonStyle.danger)
    async def steal_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        message, view = await self.cog.build_steal_prompt(interaction)
        await interaction.response.send_message(
            message,
            view=view,
            ephemeral=True,
        )


class RationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rations_sheet = None
        self.rations = {}
        self.rations_lock = asyncio.Lock()
        self.rations_storage_lock = asyncio.Lock()
        self.rations_storage_error = None
        print("Rations Cog: Loaded. Google Sheets will connect after startup.")

    def record_storage_error(self, error: Exception) -> None:
        self.rations_sheet = None
        self.rations_storage_error = error
        print(
            "CRITICAL ERROR initializing RationsCog GSheets: "
            f"{type(error).__name__}: {error}"
        )
        if isinstance(error, gspread.exceptions.SpreadsheetNotFound):
            print(
                "Share the rations spreadsheet with the service account: "
                f"{os.getenv('GOOGLE_CLIENT_EMAIL') or '<GOOGLE_CLIENT_EMAIL>'}"
            )
        traceback.print_exception(type(error), error, error.__traceback__)

    def storage_error_message(self) -> str:
        error = self.rations_storage_error
        if isinstance(error, gspread.exceptions.APIError) and error.code == 429:
            return (
                "Rations storage temporarily hit the Google Sheets rate limit. "
                "Please try again in a minute."
            )
        if isinstance(error, gspread.exceptions.SpreadsheetNotFound):
            return (
                "Rations storage could not open the spreadsheet. Ask an admin "
                "to verify the spreadsheet ID and service-account access."
            )
        if isinstance(error, gspread.exceptions.WorksheetNotFound):
            return (
                f"Rations storage could not find the '{RATIONS_SHEET_TAB_NAME}' "
                "worksheet tab. Please contact an admin."
            )

        return (
            "Rations storage is unavailable. Please contact an admin and check "
            "the bot logs."
        )

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
        rations_sheet = google_sheet.worksheet(RATIONS_SHEET_TAB_NAME)
        rations = load_sheet_rations(rations_sheet)

        local_rations = load_local_rations()
        if not rations and local_rations:
            rations = local_rations
            write_sheet_rations(rations_sheet, rations)
            print("Rations Cog: Imported local rations.json into Google Sheets.")

        self.rations_sheet = rations_sheet
        self.rations = rations
        self.rations_storage_error = None

    def save_rations(self) -> None:
        if self.rations_sheet is None:
            raise RuntimeError("Rations worksheet is unavailable.")

        write_sheet_rations(self.rations_sheet, self.rations)

    def get_entry(self, member: discord.Member) -> dict[str, object]:
        user_id = str(member.id)
        entry = self.rations.setdefault(
            user_id,
            {
                "name": member.display_name,
                "total": 0,
                "steals": DEFAULT_STEALS,
                "labor_release": "",
                "dead": 0,
            },
        )
        normalize_entry(entry)
        entry["name"] = member.display_name
        return entry

    def get_member_or_target(self, user_id: str, entry: dict[str, object]) -> discord.Member | RationTarget:
        member = self.find_member(user_id)
        if member is not None:
            return member
        return RationTarget(user_id, str(entry["name"]))

    def steal_unavailable_message(
        self,
        entry: dict[str, object],
        now: datetime,
    ) -> str:
        if is_dead(entry):
            return "You died in the labor camp and cannot steal."

        release_at = parse_labor_release(entry.get("labor_release"))
        next_steal = next_steal_gain_time(entry, now)
        if release_at is not None and release_at > now:
            if next_steal is None:
                return f"You are in the labor camp until {format_release_time(release_at)}."
            return (
                f"You are in the labor camp until {format_release_time(release_at)}. "
                f"Your next steal is gained at {format_release_time(next_steal)}."
            )

        if next_steal is not None:
            return f"Your next steal is gained at {format_release_time(next_steal)}."

        return "You cannot steal."

    def steal_target_options(
        self,
        thief_id: str,
        now: datetime,
    ) -> tuple[list[discord.SelectOption], int]:
        stealable_entries = [
            (user_id, entry)
            for user_id, entry in self.rations.items()
            if can_be_stolen_from(entry, user_id, thief_id, now)
        ]
        stealable_entries.sort(
            key=lambda item: (-int(item[1]["total"]), str(item[1]["name"]).lower())
        )

        options = [
            discord.SelectOption(
                label=str(entry["name"])[:100],
                value=user_id,
                description=f"{int(entry['total'])} ration(s) available"[:100],
            )
            for user_id, entry in stealable_entries[:25]
        ]
        return options, len(stealable_entries)

    async def connect_storage(self) -> bool:
        if self.rations_sheet is not None:
            return True

        async with self.rations_storage_lock:
            if self.rations_sheet is not None:
                return True

            try:
                await asyncio.to_thread(self.initialize_rations_sheet)
                print("Rations Cog: Connected to Google Sheets successfully.")
                return True
            except Exception as error:
                self.record_storage_error(error)
                return False

    async def storage_is_available(self, interaction: discord.Interaction) -> bool:
        if await self.connect_storage():
            return True

        await interaction.response.send_message(
            self.storage_error_message(),
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
                await asyncio.to_thread(self.save_rations)
            except Exception as error:
                entry["name"] = previous_name
                self.record_storage_error(error)

    async def refresh_member_names_once(self) -> None:
        if not await self.connect_storage():
            return

        async with self.rations_lock:
            self.rations = await asyncio.to_thread(
                load_sheet_rations,
                self.rations_sheet,
            )
            names_changed = False
            for user_id, entry in self.rations.items():
                member = self.find_member(user_id)
                if member is not None and entry["name"] != member.display_name:
                    entry["name"] = member.display_name
                    names_changed = True

            if names_changed:
                await asyncio.to_thread(self.save_rations)

    def release_due_laborers(self, now: datetime) -> list[str]:
        released_names = []
        for entry in self.rations.values():
            normalize_entry(entry)
            release_at = parse_labor_release(entry.get("labor_release"))
            if release_at is None or release_at > now:
                continue

            entry["labor_release"] = ""
            if is_dead(entry):
                continue

            entry["total"] = int(entry["total"]) + LABOR_PAYOUT
            released_names.append(str(entry["name"]))

        return released_names

    def apply_noon_ration_update(self, now: datetime) -> tuple[list[str], list[str]]:
        reset_names = []
        dead_names = []
        for entry in self.rations.values():
            normalize_entry(entry)
            if is_dead(entry):
                continue

            release_at = parse_labor_release(entry.get("labor_release"))
            was_in_labor = release_at is not None
            entry["total"] = max(0, int(entry["total"]) - 1)
            entry["steals"] = STEAL_AVAILABLE
            reset_names.append(str(entry["name"]))

            if was_in_labor and int(entry["total"]) == 0:
                entry["dead"] = 1
                entry["labor_release"] = ""
                entry["steals"] = STEAL_USED
                dead_names.append(str(entry["name"]))

        return reset_names, dead_names

    async def run_scheduled_ration_update(self, now: datetime | None = None) -> None:
        if not await self.connect_storage():
            return

        now = now or current_cst_time()
        async with self.rations_lock:
            self.rations = await asyncio.to_thread(
                load_sheet_rations,
                self.rations_sheet,
            )
            changed = False
            if now.hour == 12:
                self.apply_noon_ration_update(now)
                changed = True

            released_names = self.release_due_laborers(now)
            if released_names:
                changed = True

            if changed:
                await asyncio.to_thread(self.save_rations)

    async def settle_due_labor_releases(self) -> None:
        if not await self.connect_storage():
            return

        async with self.rations_lock:
            released_names = self.release_due_laborers(current_cst_time())
            if released_names:
                await asyncio.to_thread(self.save_rations)

    @tasks.loop(time=[dt_time(hour=0, minute=0, tzinfo=CST), dt_time(hour=12, minute=0, tzinfo=CST)])
    async def scheduled_ration_update(self) -> None:
        try:
            await self.run_scheduled_ration_update()
        except Exception as error:
            self.record_storage_error(error)

    @scheduled_ration_update.before_loop
    async def before_scheduled_ration_update(self) -> None:
        await self.bot.wait_until_ready()

    @tasks.loop(hours=3)
    async def refresh_member_names(self) -> None:
        try:
            await self.refresh_member_names_once()
        except Exception as error:
            self.record_storage_error(error)

    @refresh_member_names.before_loop
    async def before_refresh_member_names(self) -> None:
        await self.bot.wait_until_ready()

    async def cog_load(self) -> None:
        if not self.refresh_member_names.is_running():
            self.refresh_member_names.start()
        if not self.scheduled_ration_update.is_running():
            self.scheduled_ration_update.start()

    def cog_unload(self) -> None:
        self.refresh_member_names.cancel()
        self.scheduled_ration_update.cancel()

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
            previous_dead = int(entry["dead"])
            previous_labor_release = str(entry["labor_release"])
            entry["total"] = previous_total + 1
            entry["dead"] = 0
            entry["labor_release"] = ""
            try:
                await asyncio.to_thread(self.save_rations)
            except Exception as error:
                entry["total"] = previous_total
                entry["dead"] = previous_dead
                entry["labor_release"] = previous_labor_release
                self.record_storage_error(error)
                raise

        await interaction.response.send_message(
            format_ration_line(username.display_name, int(entry["total"]), entry),
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
                await asyncio.to_thread(self.save_rations)
            except Exception as error:
                entry["total"] = total
                self.record_storage_error(error)
                raise

        await interaction.response.send_message(
            format_ration_line(username.display_name, int(entry["total"]), entry),
            ephemeral=True,
        )

    async def build_steal_prompt(
        self,
        interaction: discord.Interaction,
    ) -> tuple[str, discord.ui.View | None]:
        if not await self.connect_storage():
            return self.storage_error_message(), None

        await self.settle_due_labor_releases()

        if not isinstance(interaction.user, discord.Member):
            return "You can only steal rations inside the server.", None

        thief = interaction.user
        now = current_cst_time()
        async with self.rations_lock:
            self.release_due_laborers(now)
            thief_entry = self.get_entry(thief)
            chance = caught_chance_percent(int(thief_entry["total"]))
            message = (
                "**Steal Chance**\n"
                f"{thief.display_name}: {chance}% chance of being sent to labor camp"
            )

            if (
                is_dead(thief_entry)
                or is_in_labor(thief_entry, now)
                or parse_flag(thief_entry.get("steals"), DEFAULT_STEALS) == STEAL_USED
            ):
                return (
                    f"{message}\n\n{self.steal_unavailable_message(thief_entry, now)}",
                    None,
                )

            options, total_targets = self.steal_target_options(str(thief.id), now)
            if not options:
                return f"{message}\n\nNobody can be stolen from right now.", None

            target_note = (
                "\n\nShowing the first 25 available targets."
                if total_targets > len(options)
                else ""
            )

        return (
            f"{message}\n\nSelect a target to steal 1 ration from.{target_note}",
            StealTargetView(self, thief.id, options),
        )

    async def resolve_steal_selection(
        self,
        interaction: discord.Interaction,
        target_user_id: str,
    ) -> str:
        if not await self.connect_storage():
            return self.storage_error_message()

        if not isinstance(interaction.user, discord.Member):
            return "You can only steal rations inside the server."

        await self.settle_due_labor_releases()

        thief = interaction.user
        now = current_cst_time()
        async with self.rations_lock:
            self.release_due_laborers(now)
            thief_entry = self.get_entry(thief)
            target_entry = self.rations.get(target_user_id)

            if target_entry is None:
                return "That target is no longer available."
            normalize_entry(target_entry)
            target = self.get_member_or_target(target_user_id, target_entry)

            if is_dead(thief_entry):
                return "You died in the labor camp and cannot steal."
            if is_in_labor(thief_entry, now):
                return self.steal_unavailable_message(thief_entry, now)
            if parse_flag(thief_entry.get("steals"), DEFAULT_STEALS) == STEAL_USED:
                return self.steal_unavailable_message(thief_entry, now)
            if target.id == thief.id:
                return "You cannot steal from yourself."
            if is_dead(target_entry):
                return f"{target.display_name} is dead and has nothing to steal."
            if is_in_labor(target_entry, now):
                return f"{target.display_name} is in the labor camp and cannot be stolen from."
            if int(target_entry["total"]) <= 0:
                return f"{target.display_name} has no rations to steal."

            previous_thief = dict(thief_entry)
            previous_target = dict(target_entry)
            chance = caught_chance_percent(int(thief_entry["total"]))
            caught = random.randint(1, 100) <= chance
            thief_entry["steals"] = STEAL_USED

            if caught:
                release_at = send_to_labor(thief_entry, now)
                message = (
                    f"You were caught stealing from {target.display_name} and sent "
                    f"to the labor camp until {format_release_time(release_at)}. "
                    f"Caught chance: {chance}%."
                )
            else:
                target_entry["total"] = int(target_entry["total"]) - 1
                thief_entry["total"] = int(thief_entry["total"]) + 1
                message = (
                    f"You stole 1 ration from {target.display_name}. "
                    f"{format_ration_line(thief.display_name, int(thief_entry['total']), thief_entry, now)}"
                )

            try:
                await asyncio.to_thread(self.save_rations)
            except Exception as error:
                thief_entry.update(previous_thief)
                target_entry.update(previous_target)
                self.record_storage_error(error)
                raise

        return message

    @app_commands.command(name="laborcamp", description="Volunteer for the labor camp.")
    async def volunteer_labor_camp(self, interaction: discord.Interaction) -> None:
        if not await self.storage_is_available(interaction):
            return

        await self.settle_due_labor_releases()

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "You can only volunteer for labor camp inside the server.",
                ephemeral=True,
            )
            return

        now = current_cst_time()
        async with self.rations_lock:
            entry = self.get_entry(interaction.user)
            if is_dead(entry):
                await interaction.response.send_message(
                    "You died in the labor camp.",
                    ephemeral=True,
                )
                return
            if is_in_labor(entry, now):
                await interaction.response.send_message(
                    steal_status_message(entry, now),
                    ephemeral=True,
                )
                return

            previous_entry = dict(entry)
            release_at = send_to_labor(entry, now)
            try:
                await asyncio.to_thread(self.save_rations)
            except Exception as error:
                entry.update(previous_entry)
                self.record_storage_error(error)
                raise

        await interaction.response.send_message(
            f"You volunteered for the labor camp until {format_release_time(release_at)}. "
            f"Survive until release and you will earn {LABOR_PAYOUT} rations."
        )

    @app_commands.command(name="sentencelabor", description="Send a person to labor camp.")
    @app_commands.describe(username="The person being sentenced to labor camp")
    @app_commands.checks.has_permissions(administrator=True)
    async def sentence_labor_camp(
        self,
        interaction: discord.Interaction,
        username: discord.Member,
    ) -> None:
        if not await self.storage_is_available(interaction):
            return

        await self.settle_due_labor_releases()

        now = current_cst_time()
        async with self.rations_lock:
            entry = self.get_entry(username)
            if is_dead(entry):
                await interaction.response.send_message(
                    f"{username.display_name} is already dead.",
                    ephemeral=True,
                )
                return
            if is_in_labor(entry, now):
                await interaction.response.send_message(
                    f"{username.display_name} is already in the labor camp.",
                    ephemeral=True,
                )
                return

            previous_entry = dict(entry)
            release_at = send_to_labor(entry, now)
            try:
                await asyncio.to_thread(self.save_rations)
            except Exception as error:
                entry.update(previous_entry)
                self.record_storage_error(error)
                raise

        await interaction.response.send_message(
            f"{username.display_name} has been sentenced to the labor camp until "
            f"{format_release_time(release_at)}.",
            ephemeral=True,
        )

    @app_commands.command(name="rations", description="Show everyone's rations.")
    async def show_rations(self, interaction: discord.Interaction) -> None:
        if not await self.storage_is_available(interaction):
            return

        await self.settle_due_labor_releases()
        now = current_cst_time()
        ranked_entries = sorted(
            self.rations.values(),
            key=lambda entry: (-int(entry["total"]), str(entry["name"]).lower()),
        )

        ration_lines = [
            format_ration_line(entry["name"], int(entry["total"]), entry, now)
            for entry in ranked_entries
            if int(entry["total"]) > 0
            and not is_in_labor(entry, now)
            and not is_dead(entry)
        ]
        labor_lines = [
            format_labor_line(entry["name"], int(entry["total"]), entry, now)
            for entry in sorted(
                self.rations.values(),
                key=lambda entry: str(entry["name"]).lower(),
            )
            if is_in_labor(entry, now) or is_dead(entry)
        ]
        sections = [
            "**Rations**\n"
            + ("\n".join(ration_lines) if ration_lines else "Nobody has any rations yet."),
            "**Labor Camp**\n"
            + (
                "\n".join(labor_lines)
                if labor_lines
                else "Nobody is in the labor camp."
            ),
        ]

        await interaction.response.send_message(
            "\n\n".join(sections) + "\n\nGlory to the Supreme Leader",
            view=RationsView(self),
        )

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "Only admins can change rations."
        elif self.rations_storage_error is not None:
            message = self.storage_error_message()
        else:
            message = "Something went wrong while updating rations."
        print(f"Rations command error: {error}")

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RationsCog(bot))
