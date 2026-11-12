"""
.farm panel - Add / Update / Remove Token.
Owner-locked buttons. Modal for token input.
"""

import asyncio
import disnake
from disnake.ext import commands
from disnake import ui, ButtonStyle, TextInputStyle
from bot.channel_manager import create_private_farm_channel, delete_farm_channel
from selfbot.worker import start_worker, stop_worker
from selfbot.ui import log_info, log_error


# In-memory session store: owner_id -> session dict
# session = {
#   "token": str,
#   "token_user_id": int,
#   "channel_id": int,
#   "channel": TextChannel,
#   "ws": WorkerState,
#   "bot": selfbot client,
#   "bot_task": Task,
#   "farm_task": Task,
#   "panel_message_id": int,
# }
SESSIONS: dict[int, dict] = {}
WORKER_COUNTER = 0


class TokenModal(ui.Modal):
    def __init__(self, owner_id: int, is_update: bool = False):
        self.owner_id = owner_id
        self.is_update = is_update
        components = [
            ui.TextInput(
                label="Discord User Token",
                custom_id="token_input",
                style=TextInputStyle.paragraph,
                placeholder="Paste your Discord user token here",
                required=True,
                max_length=200,
            )
        ]
        title = "Update Token" if is_update else "Add Token"
        super().__init__(title=title, components=components, custom_id=f"token_modal_{owner_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        token = inter.text_values["token_input"].strip()
        # Strip accidental quotes
        if (token.startswith('"') and token.endswith('"')) or (
            token.startswith("'") and token.endswith("'")
        ):
            token = token[1:-1].strip()

        await inter.response.defer(ephemeral=True)

        # Basic format check
        if not token or len(token) < 50:
            await inter.followup.send("Invalid discord token. Try again.", ephemeral=True)
            return

        # Validate via REST only (no gateway login — avoids session conflict)
        from selfbot.worker import validate_token

        user_data = await validate_token(token)
        if not user_data:
            await inter.followup.send("Invalid discord token. Try again.", ephemeral=True)
            return

        token_user_id = int(user_data["id"])
        token_username = user_data.get("username", "Unknown")

        guild = inter.guild
        # Check token account is in this server
        token_member = guild.get_member(token_user_id)
        if token_member is None:
            try:
                token_member = await guild.fetch_member(token_user_id)
            except Exception:
                token_member = None

        if token_member is None:
            await inter.followup.send(
                "Token valid. User is not in the server. Session not started.",
                ephemeral=True,
            )
            return

        # --- Valid + in server ---
        global WORKER_COUNTER

        if self.is_update and self.owner_id in SESSIONS:
            # Stop old session, delete old channel
            old = SESSIONS[self.owner_id]
            await inter.followup.send(
                "Stopping previous session and switching token...", ephemeral=True
            )
            await stop_worker(old)
            old_channel = old.get("channel")
            if old_channel:
                await delete_farm_channel(old_channel, delay=5.0)
            SESSIONS.pop(self.owner_id, None)

        # Create private channel
        bot_member = guild.me
        try:
            channel = await create_private_farm_channel(
                guild,
                token_member,
                bot_member,
                category_id=getattr(inter.bot, "farm_category_id", None),
            )
        except Exception as e:
            await inter.followup.send(f"Failed to create farm channel: {e}", ephemeral=True)
            return

        WORKER_COUNTER += 1
        worker_id = WORKER_COUNTER

        SESSIONS[self.owner_id] = {
            "token": token,
            "token_user_id": token_user_id,
            "channel_id": channel.id,
            "channel": channel,
            "ws": None,
            "bot": None,
            "bot_task": None,
            "farm_task": None,
            "panel_message_id": inter.message.id if inter.message else None,
        }

        # Start selfbot worker (auto-start farming)
        ws = await start_worker(
            token, channel.id, self.owner_id, worker_id, SESSIONS
        )
        if ws is None:
            await inter.followup.send(
                "Token validated but failed to start session. Check token permissions / rate limits.",
                ephemeral=True,
            )
            try:
                await channel.delete()
            except Exception:
                pass
            SESSIONS.pop(self.owner_id, None)
            return

        await inter.followup.send(
            f"Session started.\nFarm channel: {channel.mention}\nAccount: **{token_username}**",
            ephemeral=True,
        )

        # Update the original panel message to managed state
        try:
            if inter.message:
                view = ManagedPanelView(self.owner_id)
                await inter.message.edit(
                    content=f"**GhoSty Farm Panel** — owner <@{self.owner_id}>\nStatus: **Active** · Account: `{token_username}` · Channel: {channel.mention}",
                    view=view,
                )
        except Exception:
            pass


class AddTokenButton(ui.Button):
    def __init__(self, owner_id: int):
        super().__init__(
            label="Add Token",
            style=ButtonStyle.primary,
            custom_id=f"add_token_{owner_id}",
        )
        self.owner_id = owner_id

    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.owner_id:
            await inter.response.send_message(
                "This is not your panel. Make your own panel by sending `.farm`",
                ephemeral=True,
            )
            return
        await inter.response.send_modal(TokenModal(self.owner_id, is_update=False))


class UpdateTokenButton(ui.Button):
    def __init__(self, owner_id: int):
        super().__init__(
            label="Update Token",
            style=ButtonStyle.secondary,
            custom_id=f"update_token_{owner_id}",
        )
        self.owner_id = owner_id

    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.owner_id:
            await inter.response.send_message(
                "This is not your panel. Make your own panel by sending `.farm`",
                ephemeral=True,
            )
            return
        await inter.response.send_modal(TokenModal(self.owner_id, is_update=True))


class RemoveTokenButton(ui.Button):
    def __init__(self, owner_id: int):
        super().__init__(
            label="Remove Token",
            style=ButtonStyle.danger,
            custom_id=f"remove_token_{owner_id}",
        )
        self.owner_id = owner_id

    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.owner_id:
            await inter.response.send_message(
                "This is not your panel. Make your own panel by sending `.farm`",
                ephemeral=True,
            )
            return

        session = SESSIONS.get(self.owner_id)
        if not session:
            await inter.response.send_message("No active session.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        await stop_worker(session)
        channel = session.get("channel")
        if channel:
            await delete_farm_channel(channel, delay=2.0)
        SESSIONS.pop(self.owner_id, None)

        # Reset panel to fresh state
        try:
            view = FreshPanelView(self.owner_id)
            await inter.message.edit(
                content=f"**GhoSty Farm Panel** — owner <@{self.owner_id}>\nStatus: **Idle** · No token",
                view=view,
            )
        except Exception:
            pass

        await inter.followup.send("Session removed. Channel deleted.", ephemeral=True)


class FreshPanelView(ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.add_item(AddTokenButton(owner_id))


class ManagedPanelView(ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.add_item(UpdateTokenButton(owner_id))
        self.add_item(RemoveTokenButton(owner_id))


def setup_panel(bot: commands.Bot):
    @bot.command(name="farm")
    async def farm_cmd(ctx: commands.Context):
        # Only allowed in the configured farm channel
        if ctx.channel.id != bot.farm_channel_id:
            return  # silent ignore

        owner_id = ctx.author.id
        has_session = owner_id in SESSIONS and SESSIONS[owner_id].get("ws") is not None

        if has_session:
            view = ManagedPanelView(owner_id)
            status = "Active"
            session = SESSIONS[owner_id]
            ch = session.get("channel")
            mention = ch.mention if ch else "unknown"
            content = f"**GhoSty Farm Panel** — owner <@{owner_id}>\nStatus: **{status}** · Channel: {mention}"
        else:
            view = FreshPanelView(owner_id)
            content = f"**GhoSty Farm Panel** — owner <@{owner_id}>\nStatus: **Idle** · Click **Add Token** to start"

        await ctx.send(content, view=view)
