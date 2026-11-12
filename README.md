# GhoSty Commercial Solo Farm

Multi-tenant OwO farm panel for your Discord server.

Members type `.farm` → get a private panel → paste a user token → bot validates it, checks the account is in the server, creates a private channel, and starts solo lifetime farming automatically.

**Stack**
- Bot side: `disnake`
- Selfbot side: `discord.py-self`
- Sessions: in-memory (wipe on restart — test model)

## Features preserved from Ghosty (solo)

- Huntbot auto-solve + auto-restart (template matching captcha)
- Gem auto-use
- Lifetime speed mode (only mode)
- Mail claim
- OwO warning detection → auto-halt (ban prevention)
- Private farm channels (`@everyone` denied view, token user + bot allowed)

## Requirements

- Python 3.10+
- A Discord Bot (Developer Portal) with:
  - Message Content Intent
  - Server Members Intent
  - Bot invited to your server with **Administrator** (or at least Manage Channels + View + Send)
- OwO bot already in the same server
- Original captcha letter templates copied into `core/letters/`

## Setup

1. Clone / copy this folder.
2. Copy letter templates from original Ghosty repo:
   ```
   cp -r /path/to/ghosty-owo/core/letters ./core/
   ```
3. Create `.env` from the example:
   ```
   cp .env.example .env
   ```
   Fill in:
   - `BOT_TOKEN` — your bot token
   - `GUILD_ID` — your server ID
   - `FARM_CHANNEL_ID` — the channel where `.farm` is allowed
   - `FARM_CATEGORY_ID` — (optional) category for private farm channels
4. Install deps:
   ```
   pip install -r requirements.txt
   ```
5. Run:
   ```
   python main.py
   ```

## Member flow

1. Member types `.farm` in the farm channel.
2. Bot replies with a panel (only that member can use the buttons).
3. **Add Token** → Modal → paste user token.
4. Bot validates token (real login check).
5. Bot checks the token account is a member of the server.
6. If not in server → ephemeral error, no session.
7. If valid + in server → private channel created (name = current username), farming starts automatically.
8. Later `.farm` shows **Update Token** + **Remove Token**.
9. Update = stop old, delete channel after 5s, start new.
10. Remove = stop, delete channel, back to fresh panel.

## Deploy (any VPS / Railway / Render / etc.)

1. Push this folder to a private GitHub repo.
2. On the host:
   ```bash
   git clone <your-repo>
   cd ghosty-commercial
   python -m venv venv
   source venv/bin/activate   # or Windows equivalent
   pip install -r requirements.txt
   cp .env.example .env
   # edit .env
   # copy core/letters from original
   python main.py
   ```
3. For persistence use `tmux`, `screen`, or a process manager (`systemd`, `pm2`, Docker).

Example systemd unit:

```ini
[Unit]
Description=GhoSty Commercial Farm
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/ghosty-commercial
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Notes

- One active session per Discord user (the person who typed `.farm`).
- Token can belong to any account that is already in the server.
- No multi-worker quest helpers (solo only).
- No original web dashboard.
- Prefix commands on the selfbot side are disabled for members; only the panel controls the session.
- On process restart all sessions are wiped (in-memory). Re-add tokens after restart.

## Captcha templates

The solver needs the PNG letter templates from the original repo under:

```
core/letters/
  0/ a.png b.png ...
  1/ ...
  2/ ...
  3/ ...
  4/ ...
```

Without them huntbot captcha solving will fail.
