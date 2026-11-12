"""
Selfbot worker launcher.
One instance per commercial session.
"""

import asyncio
import discord
from discord.ext import commands
from .heart import WorkerState, PseudoCtx, _run_farming_loop
from .ui import log_worker_event, log_error


def create_selfbot():
    bot = commands.Bot(command_prefix=".", self_bot=True, case_insensitive=True)
    bot.remove_command("help")
    return bot


async def start_worker(token: str, channel_id: int, owner_id: int, worker_id: int, session_store: dict):
    """
    Start a single selfbot worker, farm in the given channel, auto-start.
    Returns the WorkerState or None on failure.
    """
    bot = create_selfbot()
    ws = WorkerState(worker_id, owner_id, channel_id)
    ws.bot = bot

    ready_event = asyncio.Event()
    fail_reason = {"msg": None}

    @bot.event
    async def on_ready():
        ws.username = str(bot.user)
        log_worker_event(worker_id, f"Connected as {bot.user}", "SUCCESS")
        ready_event.set()

    @bot.event
    async def on_disconnect():
        log_worker_event(worker_id, "Disconnected", "WARN")

    try:
        # Run bot in background task
        bot_task = asyncio.create_task(bot.start(token))

        # Wait for ready (max 30s)
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            fail_reason["msg"] = "Login timeout - token may be invalid"
            bot_task.cancel()
            try:
                await bot.close()
            except Exception:
                pass
            return None

        # Resolve channel
        channel = bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except Exception as e:
                fail_reason["msg"] = f"Cannot access farm channel: {e}"
                await bot.close()
                return None

        ctx = PseudoCtx(channel, bot)
        session_store[owner_id]["ws"] = ws
        session_store[owner_id]["bot"] = bot
        session_store[owner_id]["bot_task"] = bot_task

        # Auto-start farming
        farm_task = asyncio.create_task(_run_farming_loop(ctx, ws, bot))
        session_store[owner_id]["farm_task"] = farm_task

        return ws

    except discord.LoginFailure:
        fail_reason["msg"] = "Invalid token (LoginFailure)"
        return None
    except Exception as e:
        fail_reason["msg"] = str(e)
        log_error(f"Worker start failed: {e}")
        return None


async def stop_worker(session: dict):
    """Gracefully stop a running session."""
    ws = session.get("ws")
    if ws:
        ws.running = False
        ws.halted = True
    farm_task = session.get("farm_task")
    if farm_task and not farm_task.done():
        farm_task.cancel()
        try:
            await farm_task
        except (asyncio.CancelledError, Exception):
            pass
    bot = session.get("bot")
    if bot:
        try:
            await bot.close()
        except Exception:
            pass
    bot_task = session.get("bot_task")
    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except (asyncio.CancelledError, Exception):
            pass
