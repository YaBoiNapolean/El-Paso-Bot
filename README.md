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
- Session management with role-restricted start, vote, shutdown, and boost commands. Vote thresholds and active session state persist in `bot_data.json`.

## Setup

1. Install Python 3.10 or newer.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Create a Discord application and bot at the Discord Developer Portal.
4. Enable **Server Members Intent** and **Message Content Intent** under Bot settings.
5. Invite it with the `bot` and `applications.commands` scopes. Grant the permissions needed by your server: View Channels, Send Messages, Embed Links, Manage Messages, Manage Channels, Manage Roles, Moderate Members, Kick Members, Ban Members, and View Audit Log.
6. Copy `.env` and fill in every value, including `DISCORD_TOKEN`, then start it:

	Linux/macOS:
	```bash
	python main.py
	```

Never commit the token. By default, slash commands are synced globally in `setup_hook`, so Discord may take a little time to display a newly added command. For immediate testing, set `COMMAND_GUILD_ID` to the target server ID; commands will be synced directly to that server on startup.

## Role configuration

Set `STAFF_ROLE_ID`, `ADMIN_ROLE_ID`, `SESSION_ROLE_ID`, and `LOG_CHANNEL_ID` in `.env` to your Discord role and channel IDs. The bot fails closed while a required role is still `0`. `SESSION_ROLE_ID` controls all four session-management commands. `LOG_CHANNEL_ID` is the default activity-log channel; `/logging channel` can override it for an individual server, while `/logging-disable` disables that server's logging. Enable Developer Mode in Discord, then right-click each role or channel and choose **Copy ID**.

Set these `.env` values to configure the bot:

- `DISCORD_TOKEN`: bot token.
- `COMMAND_GUILD_ID`: optional test server ID for immediate command registration; leave blank for global commands.
- `ENABLE_PRIVILEGED_INTENTS`: set to `true` only after enabling Server Members Intent and Message Content Intent in the Developer Portal. Slash commands work with the default `false` value.
- `BOT_DATA_FILE`: JSON persistence path.
- `EMBED_COLOUR`: default embed color as an integer, such as `16716947` for `#ff1493`.
- `STAFF_ROLE_ID`, `ADMIN_ROLE_ID`, `SESSION_ROLE_ID`, and `LOG_CHANNEL_ID`: Discord IDs.
- `SERVER_INVITE_URL`: Discord invite URL used in the bot's presence.
- `GAME_JOIN_URL`: in-game join URL used by the **Join Game** button on session startup embeds.
- `SESSION_START_BANNER_URL`, `SESSION_VOTE_BANNER_URL`, `SESSION_SHUTDOWN_BANNER_URL`, and `SESSION_BOOST_BANNER_URL`: one image URL per session embed type.
- `STAFF_FEEDBACK_BANNER_URL`: image URL shown at the bottom of staff feedback embeds.

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
- `/staff-feedback member`: Select a 1-5 star rating and optionally add notes for a staff member.
- `/feedback-leaderboard`: Show staff ranked by average feedback rating.

### Sessions

- `/session-start`: Start a session, ping `@here`, send a join button, and DM users who voted.
- `/session-vote required_votes`: Open a vote with a green button. The session starts automatically at the requested vote count and pings `@here`.
- `/session-shutdown`: End the active session.
- `/session-boost`: Announce that the active session needs more players.

Only members with `SESSION_ROLE_ID` can run session commands. Members can vote once per vote message. Voters receive a DM when the session starts saying they will be warned if they do not join the game. The bot needs **Mention @everyone, @here, and All Roles** permission to deliver the `@here` notifications, and users must allow DMs to receive the reminder.

## Production notes

Commands with moderation permissions use both Discord's default command permissions and runtime role hierarchy checks. The bot role must be above any member or role it manages. The anti-nuke command currently enables monitoring configuration and alert-channel storage; it does not automatically ban suspected administrators, because automatic punishment based only on gateway events can lock out a server owner after a false positive. Use audit-log review and least-privilege permissions for enforcement.

## Notes

`bot_data.json` contains server configuration and should be backed up but not committed if it contains private server data. For production Railway deployments, use the Volume option above.