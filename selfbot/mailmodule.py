"""
Mail claim - solo version (exact original interaction logic).
"""

import asyncio
from datetime import datetime
import discord
from discord.interactions import _wrapped_interaction
from discord.utils import _generate_nonce
from discord.enums import InteractionType
from .ui import log_worker_event


async def execute_mail_claim(ctx, ws, bot):
    log_worker_event(ws.worker_number, "Checking mailbox...", "INFO")
    try:
        await ctx.send("owo mail")
    except Exception as e:
        log_worker_event(ws.worker_number, f"Failed to send owo mail: {e}", "WARNING")
        ws.is_mail_claiming = False
        return

    owo_bot_id = 408785106942164992
    try:
        mail_msg = None
        worker_username = bot.user.name.lower()
        worker_display = (bot.user.display_name or "").lower()
        worker_id_str = str(bot.user.id)

        for _ in range(5):
            await asyncio.sleep(2.5)
            async for m in ctx.channel.history(limit=25):
                if m.author.id == owo_bot_id:
                    msg_content = m.content.lower()
                    raw_data = {}
                    try:
                        route = discord.http.Route(
                            "GET",
                            "/channels/{channel_id}/messages?limit=1&around={message_id}",
                            channel_id=ctx.channel.id,
                            message_id=m.id,
                        )
                        req_data = await bot.http.request(route)
                        if isinstance(req_data, list) and len(req_data) > 0:
                            raw_data = req_data[0]
                    except Exception:
                        pass
                    raw_str = str(raw_data).lower()
                    is_for_me = (
                        worker_id_str in msg_content
                        or worker_username in msg_content
                        or worker_display in msg_content
                        or worker_id_str in raw_str
                        or worker_username in raw_str
                        or worker_display in raw_str
                    )
                    if not is_for_me:
                        continue
                    if "you do not have any mail" in msg_content or "you do not have any mail" in raw_str:
                        log_worker_event(ws.worker_number, "No mail found.", "INFO")
                        ws.is_mail_claiming = False
                        return
                    if "components" in raw_data and len(raw_data["components"]) > 0:
                        if (
                            "1465989917103357962" in raw_str
                            or "closed_mail" in raw_str
                            or "1465989938796433570" in raw_str
                            or "opened_mail" in raw_str
                            or "mailbox" in raw_str
                        ):
                            mail_msg = m
                            break
            if mail_msg:
                break

        if not mail_msg:
            log_worker_event(ws.worker_number, "Could not find owo mail response.", "WARNING")
            ws.is_mail_claiming = False
            return
    except Exception as e:
        log_worker_event(ws.worker_number, f"Error waiting for mail: {e}", "WARNING")
        ws.is_mail_claiming = False
        return

    def find_button_in_components(components_list, check_func, include_disabled=False):
        def _search(data, targets):
            if isinstance(data, dict):
                if data.get("type") == 2 and check_func(data):
                    if include_disabled or not data.get("disabled", False):
                        targets.append(data)
                for v in data.values():
                    _search(v, targets)
            elif isinstance(data, list):
                for item in data:
                    _search(item, targets)

        targets = []
        _search(components_list, targets)
        return targets

    def is_closed_mail(data):
        if data.get("style") == 2:
            return False
        emoji = data.get("emoji", {})
        eid = str(emoji.get("id", ""))
        ename = emoji.get("name")
        return eid in ("1465989917103357962", "1465989938796433570") or ename in (
            "closed_mail",
            "opened_mail",
        )

    def is_claim_button(data):
        lbl = str(data.get("label", "")).lower()
        emoji = data.get("emoji", {})
        return "claim" in lbl or emoji.get("name") == "🎁"

    def is_return_button(data):
        emoji = data.get("emoji", {})
        return str(emoji.get("id", "")) == "1466327293621305385" or emoji.get("name") == "return"

    def is_forward_button(data):
        emoji = data.get("emoji", {})
        return str(emoji.get("id", "")) == "1356883239175717035" or emoji.get("name") == "forward"

    def is_indicator_button(data):
        lbl = str(data.get("label", ""))
        return "/" in lbl

    async def poll_components(expected_state, timeout=12):
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                route = discord.http.Route(
                    "GET",
                    "/channels/{channel_id}/messages?limit=1&around={message_id}",
                    channel_id=ctx.channel.id,
                    message_id=mail_msg.id,
                )
                raw_data = await bot.http.request(route)
                if isinstance(raw_data, list) and len(raw_data) > 0:
                    raw_data = raw_data[0]
                components = raw_data.get("components", [])
                if expected_state(components):
                    return components
            except Exception:
                pass
            await asyncio.sleep(1.5)
        return []

    max_mails = 25
    mails_claimed = 0

    for _ in range(max_mails):
        def check_main_menu(comps):
            return len(find_button_in_components(comps, is_closed_mail)) > 0 or len(
                find_button_in_components(comps, is_return_button)
            ) == 0

        components = await poll_components(check_main_menu, timeout=12)
        closed_mail_buttons = find_button_in_components(components, is_closed_mail)
        if not closed_mail_buttons:
            forward_buttons = find_button_in_components(components, is_forward_button)
            if forward_buttons:
                indicator_buttons = find_button_in_components(
                    components, is_indicator_button, include_disabled=True
                )
                old_indicator = str(indicator_buttons[0].get("label", "")) if indicator_buttons else ""
                can_move_forward = True
                if old_indicator and "/" in old_indicator:
                    parts = old_indicator.split("/")
                    if len(parts) == 2 and parts[0].strip() == parts[1].strip():
                        can_move_forward = False
                if can_move_forward:
                    try:
                        await _wrapped_interaction(
                            mail_msg._state,
                            _generate_nonce(),
                            InteractionType.component,
                            None,
                            ctx.channel,
                            forward_buttons[0],
                            message=mail_msg,
                        )
                    except Exception as e:
                        log_worker_event(ws.worker_number, f"Failed next page: {e}", "WARNING")
                        break

                    def check_page_changed(comps):
                        ind_btns = find_button_in_components(
                            comps, is_indicator_button, include_disabled=True
                        )
                        if not ind_btns:
                            return False
                        return str(ind_btns[0].get("label", "")) != old_indicator

                    await poll_components(check_page_changed, timeout=12)
                    continue
            if mails_claimed > 0:
                log_worker_event(
                    ws.worker_number, f"Claimed {mails_claimed} mails. Done.", "SUCCESS"
                )
            else:
                log_worker_event(ws.worker_number, "No claimable mail found.", "INFO")
            break

        target_btn = closed_mail_buttons[0]
        try:
            await _wrapped_interaction(
                mail_msg._state,
                _generate_nonce(),
                InteractionType.component,
                None,
                ctx.channel,
                target_btn,
                message=mail_msg,
            )
        except Exception as e:
            log_worker_event(ws.worker_number, f"Failed open mail: {e}", "WARNING")
            break

        def check_detail_menu(comps):
            return len(find_button_in_components(comps, is_return_button)) > 0

        components = await poll_components(check_detail_menu, timeout=12)
        claim_buttons = find_button_in_components(components, is_claim_button)
        if claim_buttons:
            try:
                await _wrapped_interaction(
                    mail_msg._state,
                    _generate_nonce(),
                    InteractionType.component,
                    None,
                    ctx.channel,
                    claim_buttons[0],
                    message=mail_msg,
                )
                mails_claimed += 1
                await asyncio.sleep(2)
            except Exception as e:
                log_worker_event(ws.worker_number, f"Failed claim: {e}", "WARNING")

        components = await poll_components(check_detail_menu, timeout=5)
        return_buttons = find_button_in_components(components, is_return_button)
        if return_buttons:
            try:
                await _wrapped_interaction(
                    mail_msg._state,
                    _generate_nonce(),
                    InteractionType.component,
                    None,
                    ctx.channel,
                    return_buttons[0],
                    message=mail_msg,
                )
            except Exception as e:
                log_worker_event(ws.worker_number, f"Failed return: {e}", "WARNING")
                break
        else:
            break

    ws.is_mail_claiming = False
