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
