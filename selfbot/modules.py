"""
Solo speed modes + zoo / gem parsers.
Lifetime is the only active mode for commercial panels.
"""

import re
import asyncio as made_by_ghosty
from .ui import log_worker_event

SPEED_MODES = {
    "lifetime": {
        "name": "Lifetime (Ultra Long - Detection Bypass)",
        "command_delay": 0.4,
        "action_delay_min": 7.0,
        "action_delay_max": 22.0,
        "random_long_delay_min": 250,
        "random_long_delay_max": 550,
        "gem_check_interval_min": 220,
        "gem_check_interval_max": 380,
        "work_duration_min": 3 * 3600,
        "work_duration_max": 5 * 3600,
        "break_duration_min": 10 * 3600,
        "break_duration_max": 14 * 3600,
        "day_skip_threshold": 3,
        "day_skip_duration": 24 * 3600,
    }
}


def format_value(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return str(value)


async def parse_zoo_message(zoo_messages):
    combined_message = "\n".join(zoo_messages)

    superscript_map = {
        "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
        "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    }

    value_map = {
        "common": {"cash": 1, "essence": 1},
        "uncommon": {"cash": 3, "essence": 5},
        "rare": {"cash": 10, "essence": 20},
        "epic": {"cash": 250, "essence": 250},
        "mythic": {"cash": 5000, "essence": 3000},
        "legendary": {"cash": 15000, "essence": 10000},
        "fabled": {"cash": 250000, "essence": 100000},
        "special": {"cash": 6000, "essence": 5000},
        "hidden": {"cash": 1000000, "essence": 500000},
        "patreon": {"cash": 1000, "essence": 500},
        "cpatreon": {"cash": 50000, "essence": 25000},
        "gem": {"cash": 30000, "essence": 20000},
        "distorted": {"cash": 300000, "essence": 200000},
        "bot": {"cash": 50000, "essence": 10000},
    }

    lines = combined_message.split("\n")
    tier_counts = {tier: 0 for tier in value_map}
    current_tier = None

    for line in lines:
        tier_match = re.search(r"<a?:(\w+):\d+>", line)
        if tier_match:
            tier_name = tier_match.group(1).lower()
            if tier_name == "botrank":
                tier_name = "bot"
            if tier_name in value_map:
                current_tier = tier_name

        if current_tier:
            superscript_regex = r"([⁰¹²³⁴⁵⁶⁷⁸⁹]+)"
            for match in re.finditer(superscript_regex, line):
                superscript_str = match.group(1)
                number_str = "".join(superscript_map.get(char, char) for char in superscript_str)
                if number_str.isdigit():
                    tier_counts[current_tier] += int(number_str)

    total_cash = 0
    total_essence = 0
    for tier, count in tier_counts.items():
        if count > 0 and tier in value_map:
            total_cash += count * value_map[tier]["cash"]
            total_essence += count * value_map[tier]["essence"]

    zoo_points = 0
    zoo_points_patterns = [
        r"Zoo Points?:\s*__?([\d,]+)__?",
        r"Points?:\s*__?([\d,]+)__?",
        r"__?([\d,]+)__?\s*Zoo Points?",
        r"Zoo Points?:\s*([\d,]+)",
    ]
    for pattern in zoo_points_patterns:
        match = re.search(pattern, combined_message, re.IGNORECASE)
        if match:
            zoo_points = int(match.group(1).replace(",", ""))
            break

    return {
        "total_cash": total_cash,
        "total_essence": total_essence,
        "zoo_points": zoo_points,
        "tier_counts": tier_counts,
    }


async def fetch_zoo_data(ctx):
    await ctx.send("owo zoo")
    await made_by_ghosty.sleep(5)
    try:
        messages = [msg async for msg in ctx.channel.history(limit=10)]
        zoo_messages = []
        for msg in messages:
            if msg.author.id == 408785106942164992:
                content_lower = msg.content.lower()
                if any(kw in content_lower for kw in ["zoo", "animals", "cowoncy", "points:"]) or any(
                    sup in msg.content for sup in "⁰¹²³⁴⁵⁶⁷⁸⁹"
                ):
                    zoo_messages.append(msg.content)
                    if "common" in content_lower:
                        break
        if zoo_messages:
            zoo_messages.reverse()
            return await parse_zoo_message(zoo_messages)
        return None
    except Exception as e:
        log_worker_event("ZOO", f"Error fetching zoo data: {e}", "WARNING")
        return None


async def parse_gems(inventory_message):
    rarity_order = ["f", "l", "m", "e", "r", "u", "c"]
    gems_by_tier = {"1": [], "2": [], "3": [], "4": []}
    lines = inventory_message.split("\n")
    for line in lines:
        for tier in ["1", "2", "3", "4"]:
            for rarity in rarity_order:
                pattern = fr"`(\d+)`<a?:({rarity}gem{tier}):\d+>"
                match = re.search(pattern, line)
                if match:
                    gem_number = match.group(1)
                    gems_by_tier[tier].append((rarity, gem_number))
    for tier in gems_by_tier:
        gems_by_tier[tier].sort(key=lambda x: rarity_order.index(x[0]))
    selected_gems = []
    for tier in ["1", "2", "3", "4"]:
        if gems_by_tier[tier]:
            selected_gems.append(gems_by_tier[tier][0][1])
    return selected_gems
