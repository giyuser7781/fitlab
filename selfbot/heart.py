"""
Solo farming heart - lifetime mode only.
Huntbot + gem + mail + warning detection + auto-halt.
"""

import random as ghostyjija
import re
import asyncio as made_by_ghosty
from datetime import datetime, timedelta
from .modules import SPEED_MODES, parse_gems, format_value
from .ghostycorehb import GhoStySolveNormalCap, GhoStySyncedCaptchaSolve
from .ui import log_worker_event
from .mailmodule import execute_mail_claim


class WorkerState:
    def __init__(self, worker_number, owner_id, channel_id):
        self.worker_number = worker_number
        self.owner_id = owner_id
        self.channel_id = channel_id
        self.bot = None
        self.username = "Unknown"
        self.running = False
        self.has_started = False
        self.sleep_mode = False
        self.farming_start_time = None
        self.sleep_start_time = None
        self.ghosty_start_time = datetime.now()
        self.ghosty_commands_sent = 0
        self.ghosty_gems_used = 0
        self.last_gem_check = 0
        self.current_speed_mode = "lifetime"
        self.lifetime_work_cycles = 0
        self.lifetime_day_skip_active = False
        self.lifetime_cycle_start_time = None
        self.initial_cash = 0
        self.current_cash = 0
        self.GhoStyHbAlrActiveVar = False
        self.GhoStyCoreAvailCheck = True
        self.huntbot_enabled = True
        self.paused = False
        self.pause_end_time = None
        self.is_mail_claiming = False
        self.last_mail_claim = None
        self.warning_count = 0
        self.halted = False


class PseudoCtx:
    def __init__(self, channel, bot):
        self.channel = channel
        self.bot = bot
        self.send = channel.send


def ParseGhoStyTimeStrs(time_str):
    time_str = time_str.upper().strip()
    h = int(re.search(r"(\d+)H", time_str).group(1)) if "H" in time_str else 0
    m = int(re.search(r"(\d+)M", time_str).group(1)) if "M" in time_str else 0
    return timedelta(hours=h, minutes=m)


async def GhoStyCapUrlSolver(url):
    try:
        if GhoStySolveNormalCap:
            try:
                return await GhoStySolveNormalCap(url)
            except Exception:
                pass
        if GhoStySyncedCaptchaSolve:
            try:
                return GhoStySyncedCaptchaSolve(url)
            except Exception:
                pass
    except Exception:
        pass
    return None


async def CheckGhoStyHbMsgFetch(ctx, ws, cowoncy_amount=None):
    if not ws.huntbot_enabled or ws.halted:
        return False
    try:
        await made_by_ghosty.sleep(1)
        messages = [msg async for msg in ctx.channel.history(limit=5)]
        for msg in messages:
            if msg.author.id != 408785106942164992:
                continue
            msg_content = str(msg.content)
            if not msg_content and msg.embeds:
                embed = msg.embeds[0]
                msg_content = (embed.description or "") + "".join(
                    f"{f.name}\n{f.value}" for f in embed.fields
                )
            msg_content_lower = msg_content.lower()

            if "beep. boop. i am huntbot" in msg_content_lower:
                optimal = 20000
                try:
                    match = re.search(
                        r"current max autohunt:.*?for (\d+) cowoncy",
                        msg_content_lower.replace(",", ""),
                    )
                    if match:
                        optimal = int(match.group(1))
                except Exception:
                    pass
                log_worker_event(ws.worker_number, f"HuntBot optimal: {optimal}", "INFO")
                await made_by_ghosty.sleep(2)
                await ctx.send(f"owo hb {optimal}")
                await made_by_ghosty.sleep(4)
                return await CheckGhoStyHbMsgFetch(ctx, ws, optimal)

            if "i will be back in" in msg_content_lower:
                match = re.search(r"i will be back in (\d+h\s*\d*m?|\d+m)", msg_content_lower)
                if match:
                    delta = ParseGhoStyTimeStrs(match.group(1).strip())
                    ws.GhoStyHbAlrActiveVar = True
                    log_worker_event(
                        ws.worker_number, f"Next huntbot in {delta}", "INFO"
                    )
                    return True

            if "here is your password!" in msg_content_lower and msg.attachments:
                url = msg.attachments[0].url
                log_worker_event(ws.worker_number, f"Solving captcha...", "DEBUG")
                result = await GhoStyCapUrlSolver(url)
                if result:
                    use_cowoncy = cowoncy_amount or 20000
                    await made_by_ghosty.sleep(2)
                    await ctx.send(f"owo autohunt {use_cowoncy} {result}")
                    log_worker_event(
                        ws.worker_number, f"Auto-solved HuntBot: {result}", "SUCCESS"
                    )
                    await made_by_ghosty.sleep(4)
                    return await CheckGhoStyHbMsgFetch(ctx, ws, use_cowoncy)
                else:
                    log_worker_event(
                        ws.worker_number, "Captcha solver failed", "WARNING"
                    )
                    return False

            if (
                "you spent" in msg_content_lower
                and "cowoncy" in msg_content_lower
                and "i will be back in" in msg_content_lower
            ):
                match = re.search(r"i will be back in (\d+h\s*\d*m?|\d+m)", msg_content_lower)
                if match:
                    delta = ParseGhoStyTimeStrs(match.group(1).strip())
                    ws.GhoStyHbAlrActiveVar = True
                    log_worker_event(ws.worker_number, f"Hunt active. Back in {delta}", "INFO")
                    return True

            if "i am back with" in msg_content_lower and "animals" in msg_content_lower:
                log_worker_event(ws.worker_number, "Hunt completed!", "SUCCESS")
                await made_by_ghosty.sleep(15)
                await ctx.send("owo hb")
                await made_by_ghosty.sleep(4)
                return await CheckGhoStyHbMsgFetch(ctx, ws)
        return False
    except Exception as e:
        log_worker_event(ws.worker_number, f"HB error: {e}", "WARNING")
        return False


async def _do_gem_check(ctx, ws):
    if ws.sleep_mode or ws.paused or ws.halted:
        return
    await ctx.send("owo lb all")
    await made_by_ghosty.sleep(2)
    await ctx.send("owo inventory")
    await made_by_ghosty.sleep(3)
    try:
        latest = [msg async for msg in ctx.channel.history(limit=3)]
        for message in latest:
            if message.author.id == 408785106942164992 and "inventory" in message.content.lower():
                gem_numbers = await parse_gems(message.content)
                if gem_numbers:
                    gems_str = " ".join(gem_numbers)
                    await ctx.send(f"owo use {gems_str}")
                    ws.ghosty_gems_used += len(gem_numbers)
                    log_worker_event(
                        ws.worker_number, f"Used gems: {gems_str}", "SUCCESS"
                    )
                break
    except Exception as e:
        log_worker_event(ws.worker_number, f"Gem check error: {e}", "WARNING")
    ws.last_gem_check = datetime.now().timestamp()


async def _run_farming_loop(ctx, ws, bot):
    """Main solo farming loop - lifetime mode, auto-start."""
    mode = SPEED_MODES["lifetime"]
    ws.running = True
    ws.has_started = True
    ws.farming_start_time = datetime.now()
    ws.lifetime_cycle_start_time = datetime.now()
    log_worker_event(ws.worker_number, "Farming started (lifetime mode)", "SUCCESS")

    # Initial huntbot kick
    if ws.huntbot_enabled:
        await ctx.send("owo hb")
        await made_by_ghosty.sleep(3)
        await CheckGhoStyHbMsgFetch(ctx, ws)

    work_end = datetime.now() + timedelta(
        seconds=ghostyjija.uniform(mode["work_duration_min"], mode["work_duration_max"])
    )
    next_gem = datetime.now() + timedelta(
        seconds=ghostyjija.uniform(mode["gem_check_interval_min"], mode["gem_check_interval_max"])
    )
    next_mail = datetime.now() + timedelta(minutes=ghostyjija.randint(30, 90))
    commands = ["owo h", "owo b", "owo hunt", "owo battle"]

    while ws.running and not ws.halted:
        try:
            if ws.paused:
                if ws.pause_end_time and datetime.now() >= ws.pause_end_time:
                    ws.paused = False
                    ws.pause_end_time = None
                else:
                    await made_by_ghosty.sleep(5)
                    continue

            if ws.sleep_mode:
                if ws.sleep_start_time and datetime.now() >= ws.sleep_start_time + timedelta(
                    seconds=ghostyjija.uniform(
                        mode["break_duration_min"], mode["break_duration_max"]
                    )
                ):
                    ws.sleep_mode = False
                    ws.lifetime_work_cycles += 1
                    work_end = datetime.now() + timedelta(
                        seconds=ghostyjija.uniform(
                            mode["work_duration_min"], mode["work_duration_max"]
                        )
                    )
                    log_worker_event(ws.worker_number, "Woke from sleep", "INFO")
                else:
                    await made_by_ghosty.sleep(10)
                    continue

            # Lifetime work window expired -> sleep
            if datetime.now() >= work_end and not ws.sleep_mode:
                ws.sleep_mode = True
                ws.sleep_start_time = datetime.now()
                log_worker_event(ws.worker_number, "Entering sleep (lifetime cycle)", "INFO")
                continue

            # Warning detection (OwO bot messages)
            try:
                recent = [m async for m in ctx.channel.history(limit=8)]
                for m in recent:
                    if m.author.id == 408785106942164992:
                        content = (m.content or "").lower()
                        if any(
                            w in content
                            for w in [
                                "you have been banned",
                                "you are banned",
                                "warning",
                                "please stop",
                                "slow down",
                                "you have been timed out",
                            ]
                        ):
                            ws.warning_count += 1
                            log_worker_event(
                                ws.worker_number,
                                f"OwO warning detected ({ws.warning_count})",
                                "CRITICAL",
                            )
                            if ws.warning_count >= 1:
                                ws.halted = True
                                ws.running = False
                                log_worker_event(
                                    ws.worker_number,
                                    "Auto-halt after warning (ban prevention)",
                                    "FATAL",
                                )
                                return
            except Exception:
                pass

            # Gem check
            if datetime.now() >= next_gem:
                await _do_gem_check(ctx, ws)
                next_gem = datetime.now() + timedelta(
                    seconds=ghostyjija.uniform(
                        mode["gem_check_interval_min"], mode["gem_check_interval_max"]
                    )
                )

            # Mail claim
            if datetime.now() >= next_mail and not ws.is_mail_claiming:
                ws.is_mail_claiming = True
                await execute_mail_claim(ctx, ws, bot)
                next_mail = datetime.now() + timedelta(minutes=ghostyjija.randint(45, 120))

            # Huntbot check occasionally
            if ws.huntbot_enabled and ghostyjija.random() < 0.08:
                await CheckGhoStyHbMsgFetch(ctx, ws)

            # Main command
            cmd = ghostyjija.choice(commands)
            await ctx.send(cmd)
            ws.ghosty_commands_sent += 1

            delay = ghostyjija.uniform(mode["action_delay_min"], mode["action_delay_max"])
            if ghostyjija.random() < 0.12:
                delay += ghostyjija.uniform(
                    mode["random_long_delay_min"], mode["random_long_delay_max"]
                )
            await made_by_ghosty.sleep(delay)

        except Exception as e:
            log_worker_event(ws.worker_number, f"Loop error: {e}", "WARNING")
            await made_by_ghosty.sleep(10)

    log_worker_event(ws.worker_number, "Farming loop ended", "INFO")
