"""
Private channel creation / deletion / permission overwrites.
"""

import disnake
from disnake import PermissionOverwrite


async def create_private_farm_channel(
    guild: disnake.Guild,
    token_member: disnake.Member,
    bot_member: disnake.Member,
    category_id: int | None = None,
) -> disnake.TextChannel:
    """
    Create a private text channel named after the token user's current username.
    @everyone: deny view_channel
    token user: allow view + send
    bot: allow view + send + manage
    Administrators still see it by default.
    """
    name = token_member.display_name or token_member.name
    # Discord channel names: lowercase, no spaces preferred, max 100
    safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in name.lower())[:90]
    if not safe_name:
        safe_name = f"farm-{token_member.id}"

    overwrites = {
        guild.default_role: PermissionOverwrite(view_channel=False),
        token_member: PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        ),
        bot_member: PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
        ),
    }

    category = None
    if category_id:
        category = guild.get_channel(category_id)

    channel = await guild.create_text_channel(
        name=safe_name,
        overwrites=overwrites,
        category=category,
        reason=f"GhoSty farm channel for {token_member}",
    )
    return channel


async def delete_farm_channel(channel: disnake.TextChannel, delay: float = 5.0):
    """Delete channel after optional delay (loading buffer)."""
    if delay > 0:
        await disnake.utils.sleep_until(
            disnake.utils.utcnow() + disnake.utils.timedelta(seconds=delay)
        )
    try:
        await channel.delete(reason="GhoSty farm session ended")
    except Exception:
        pass
