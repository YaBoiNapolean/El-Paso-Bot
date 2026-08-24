# El Paso RP Mod-Bot

Neon pink, slash-command moderation for an El Paso, Texas roleplay community. The bot is intentionally small to deploy: the source is [main.py](main.py), dependencies are in [requirements.txt](requirements.txt), and runtime settings are stored in a generated `bot_data.json` file.

## Features

- Full slash-command moderation: ban, unban, softban, kick, timeout, untimeout, warn, warning history, clear warnings, purge, slowmode, lock, unlock, nickname, and role management.
- AFK status with automatic return detection, mention notices, and an `[AFK]` nickname prefix that restores the original nickname when removed.
- Sticky channel messages with automatic reposting.
- Activity logging for joins, leaves, message edits/deletions, channel changes, role changes, and bans/unbans, with a configurable log channel.
- Anti-nuke configuration with an alert-channel foundation for dangerous-action monitoring.
- Roblox tax calculator, server and user info, latency ping, and a complete command directory.
- Administrator-only `/say`, with plain text or embed mode and a custom hex color.
- Mention the bot by itself for a neon pink profile/status panel.

## Setup

1. Install Python 3.10 or newer.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Create a Discord application and bot at the Discord Developer Portal.
4. Enable **Server Members Intent** and **Message Content Intent** under Bot settings.
5. Invite it with the `bot` and `applications.commands` scopes. Grant the permissions needed by your server: View Channels, Send Messages, Embed Links, Manage Messages, Manage Channels, Manage Roles, Moderate Members, Kick Members, Ban Members, and View Audit Log.
6. Set the token and start it:

	Linux/macOS:
	```bash
	export DISCORD_TOKEN="your-token"
	python main.py
	```

	Windows PowerShell:
	```powershell
	$env:DISCORD_TOKEN = "your-token"
	python main.py
	```

Never commit the token. Slash commands are synced globally in `setup_hook`, so Discord may take a little time to display a newly added command.

## Role configuration

At the top of `main.py`, replace `STAFF_ROLE_ID = 0`, `ADMIN_ROLE_ID = 0`, and `LOG_CHANNEL_ID = 0` with your Discord role and channel IDs. The bot fails closed while either required role is still `0`. `LOG_CHANNEL_ID` is the default activity-log channel; `/logging channel` can override it for an individual server, while `/logging-disable` disables that server's logging. Enable Developer Mode in Discord, then right-click each role or channel and choose **Copy ID**.

Staff access is required for `/kick`, `/timeout`, `/untimeout`, `/warn`, `/warnings`, `/clearwarnings`, `/purge`, `/slowmode`, `/nickname`, `/say`, `/sticky`, and `/sticky-remove`.

Admin access is required for the more dangerous `/ban`, `/unban`, `/softban`, `/lock`, `/unlock`, `/role`, `/logging`, `/logging-disable`, `/antinuke`, and `/antinuke-disable` commands. Admin commands require the admin role, not merely the staff role.

No custom role is required for `/ping`, `/directory`, `/help`, `/tax`, `/afk`, `/afk-remove`, `/serverinfo`, or `/userinfo`. Discord's normal command and bot permission checks still apply where relevant.

## Railway deployment

1. Push this repository to GitHub and create a new Railway project from the repository.
2. Set the service start command to `python main.py`.
3. Add the variable `DISCORD_TOKEN` in Railway Variables. Do not put the token in the repository.
4. Deploy. Railway will install the pinned dependency from `requirements.txt`.
5. Optional: attach a Railway Volume mounted at `/data`, then set `BOT_DATA_FILE=/data/bot_data.json` so warnings, AFK states, stickies, and settings survive redeploys. Without a volume, Railway's filesystem is ephemeral.

This is a worker bot and does not need an HTTP web server or a Railway `PORT` listener. Keep the service running; do not use a one-shot command. Discord's privileged intents must still be enabled in the Developer Portal.

## Command directory

Run `/directory` in Discord for the live, in-bot directory. It is maintained at the top of `main.py`; add every new slash command there when extending the bot.

### Moderation

- `/ban member reason`: Permanently ban a member.
- `/unban user_id`: Unban a user by numeric Discord ID.
- `/softban member reason`: Ban and immediately unban, removing recent messages.
- `/kick member reason`: Kick a member.
- `/timeout member minutes reason`: Timeout for 1-40,320 minutes.
- `/untimeout member`: Remove a timeout.
- `/warn member reason`: Add a persistent warning and log it.
- `/warnings member`: View a member's warning history privately.
- `/clearwarnings member`: Delete a member's warning history.
- `/purge amount`: Delete 1-100 recent messages.
- `/slowmode seconds`: Set channel slowmode from 0-21,600 seconds.
- `/lock` and `/unlock`: Change the default role's channel access.
- `/nickname member name`: Set or clear a nickname.
- `/role member role action`: Add or remove a role.
- `/serverinfo`: Show server owner, member, channel, role, and creation details.
- `/userinfo member`: Show account, join, ID, and top-role details.

### Safety and logging

- `/logging channel`: Select the channel for activity embeds.
- `/logging-disable`: Stop activity embeds.
- `/antinuke alert_channel`: Enable anti-nuke monitoring and optionally store an alert channel.
- `/antinuke-disable`: Disable anti-nuke monitoring.
- `/sticky text`: Repost one sticky message after new messages in the current channel.
- `/sticky-remove`: Remove the current channel's sticky.

### Utility

- `/afk reason` and `/afk-remove`: Manage AFK status, automatic mention notices, and `[AFK]` nickname tagging. Sending a message also clears AFK automatically.
- `/say text use_embed color`: Administrator-only bot-authored text or embed output; color accepts hex such as `#ff1493`.
- `/tax robux`: Show the 30% Roblox tax result and required charge.
- `/ping`: Show latency and operational status.
- `/directory`: Show the same live command map maintained in `main.py`.
- `/help`: Show the El Paso RP overview.

## Production notes

Commands with moderation permissions use both Discord's default command permissions and runtime role hierarchy checks. The bot role must be above any member or role it manages. The anti-nuke command currently enables monitoring configuration and alert-channel storage; it does not automatically ban suspected administrators, because automatic punishment based only on gateway events can lock out a server owner after a false positive. Use audit-log review and least-privilege permissions for enforcement.

## Notes

`bot_data.json` contains server configuration and should be backed up but not committed if it contains private server data. For production Railway deployments, use the Volume option above.