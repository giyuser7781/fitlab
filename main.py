"""
GhoSty Commercial Solo Farm
Bot (disnake) + Selfbots (discord.py-self)
In-memory sessions. One farm channel. Private channels per token.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import disnake
from disnake.ext import commands

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
FARM_CHANNEL_ID = int(os.getenv("FARM_CHANNEL_ID", "0"))
FARM_CATEGORY_ID = os.getenv("FARM_CATEGORY_ID") or None
if FARM_CATEGORY_ID:
    FARM_CATEGORY_ID = int(FARM_CATEGORY_ID)

if not BOT_TOKEN or not GUILD_ID or not FARM_CHANNEL_ID:
    raise SystemExit("Missing BOT_TOKEN / GUILD_ID / FARM_CHANNEL_ID in .env")

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=".",
    intents=intents,
    help_command=None,
    test_guilds=[GUILD_ID],
)

bot.farm_channel_id = FARM_CHANNEL_ID
bot.farm_category_id = FARM_CATEGORY_ID
bot.guild_id = GUILD_ID


@bot.event
async def on_ready():
    print(f"[BOT] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[BOT] Guild: {GUILD_ID} | Farm channel: {FARM_CHANNEL_ID}")
    print("[BOT] Ready. Members can type .farm in the farm channel.")


# Load panel commands
from bot.panel import setup_panel
setup_panel(bot)


if __name__ == "__main__":
    bot.run(BOT_TOKEN)
