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
        stolen_from = (
            parse_flag(row[stolen_from_index], 0)
            if stolen_from_index is not None and len(row) > stolen_from_index
            else 0
        )
        time_stolen = (
            str(row[time_stolen_index]).strip()
            if time_stolen_index is not None and len(row) > time_stolen_index
            else ""
        )
        time_alive = (
            str(row[time_alive_index]).strip()
            if time_alive_index is not None and len(row) > time_alive_index
            else ""
        )

        entry = normalize_entry(
            {
                "name": name or user_id,
                "total": total,
                "steals": steals,
                "labor_release": labor_release,
                "dead": dead,
                "stolen_from": stolen_from,
                "time_stolen": time_stolen,
                "time_alive": time_alive,
            }
        )
        if not time_alive:
            needs_normalization = True
        if refresh_stolen_from_state(entry, now):
            needs_normalization = True
        rations[user_id] = entry

    if needs_normalization:
        write_sheet_rations(worksheet, rations)

    return rations


def ration_emojis(total: int) -> str:
    bowls, rice_balls = divmod(total, 5)
    return ("🍚" * bowls) + ("🍙" * rice_balls)


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


def give_reward_chance_percent(total_after_gift: int) -> int:
    effective_total = max(GIVE_MIN_RATIONS_TO_GIVE, total_after_gift)
    return min(
        GIVE_REWARD_MAX_PERCENT,
        max(GIVE_REWARD_MIN_PERCENT, 100 // effective_total),
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
        and not was_recently_stolen_from(entry, now)
        and int(entry["total"]) > 0
    )


def stolen_from_cooldown_message(
    name: object,
    entry: dict[str, object],
    now: datetime,
) -> str:
    reset_at = stolen_from_reset_time(entry, now)
    if reset_at is None:
        return f"{name} was already stolen from recently."
    return (
        f"{name} was already stolen from recently. "
        f"They can be stolen from again at {format_release_time(reset_at)}."
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
