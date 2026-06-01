import asyncio
import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


DATA_FILE = Path(__file__).with_name("rations.json")


def load_rations() -> dict[str, dict[str, object]]:
    if not DATA_FILE.exists():
        return {}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def ration_emojis(total: int) -> str:
    bowls, rice_balls = divmod(total, 5)
    return ("🍚" * bowls) + ("🍙" * rice_balls)


class RationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rations = load_rations()
        self.rations_lock = asyncio.Lock()

    def save_rations(self) -> None:
        temporary_file = DATA_FILE.with_suffix(".tmp")
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(self.rations, file, indent=2, ensure_ascii=False)
        temporary_file.replace(DATA_FILE)

    def get_entry(self, member: discord.Member) -> dict[str, object]:
        user_id = str(member.id)
        entry = self.rations.setdefault(
            user_id,
            {"name": member.display_name, "total": 0},
        )
        entry["name"] = member.display_name
        return entry

    @app_commands.command(name="addration", description="Add one ration to a person.")
    @app_commands.describe(username="The person receiving a ration")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_ration(
        self,
        interaction: discord.Interaction,
        username: discord.Member,
    ) -> None:
        async with self.rations_lock:
            entry = self.get_entry(username)
            entry["total"] = int(entry["total"]) + 1
            self.save_rations()

        await interaction.response.send_message(
            f"{username.display_name}: {ration_emojis(int(entry['total']))}",
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
            self.save_rations()

        display = ration_emojis(int(entry["total"])) or "No rations"
        await interaction.response.send_message(
            f"{username.display_name}: {display}",
            ephemeral=True,
        )

    @app_commands.command(name="showrations", description="Show everyone's rations.")
    async def show_rations(self, interaction: discord.Interaction) -> None:
        ranked_entries = sorted(
            self.rations.values(),
            key=lambda entry: (-int(entry["total"]), str(entry["name"]).lower()),
        )
        lines = [
            f"{entry['name']}: {ration_emojis(int(entry['total']))}"
            for entry in ranked_entries
            if int(entry["total"]) > 0
        ]

        await interaction.response.send_message(
            "\n".join(lines) if lines else "Nobody has any rations yet."
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
