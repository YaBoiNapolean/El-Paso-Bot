"""El Paso, Texas roleplay moderation bot."""

import json
import os
from datetime import timedelta
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

PINK = discord.Colour.from_rgb(255, 20, 147)
TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = Path(os.getenv("BOT_DATA_FILE", "bot_data.json"))

# Replace these with the Discord role IDs used by your server.
STAFF_ROLE_ID = 0
ADMIN_ROLE_ID = 0
SESSION_ROLE_ID = 0
LOG_CHANNEL_ID = 0
SERVER_INVITE_URL = os.getenv("SERVER_INVITE_URL", "")
SESSION_START_BANNER_URL = os.getenv("SESSION_START_BANNER_URL", "")
SESSION_VOTE_BANNER_URL = os.getenv("SESSION_VOTE_BANNER_URL", "")
SESSION_SHUTDOWN_BANNER_URL = os.getenv("SESSION_SHUTDOWN_BANNER_URL", "")
SESSION_BOOST_BANNER_URL = os.getenv("SESSION_BOOST_BANNER_URL", "")

COMMAND_DIRECTORY = {
    "Moderation": {
        "/ban": "Ban a member with a reason.", "/unban": "Unban a user by ID.",
        "/softban": "Ban then unban to clear recent messages.", "/kick": "Kick a member.",
        "/timeout": "Timeout a member for 1-28 days.", "/untimeout": "Remove a timeout.",
        "/warn": "Issue a logged warning.", "/warnings": "View warnings.",
        "/clearwarnings": "Clear warnings.", "/purge": "Delete up to 100 messages.",
        "/slowmode": "Set channel slowmode.", "/lock": "Lock a channel.",
        "/unlock": "Unlock a channel.", "/nickname": "Set or clear a nickname.",
        "/role": "Add or remove a role.", "/serverinfo": "Show server details.",
        "/userinfo": "Show member details.",
    },
    "Safety and logging": {
        "/logging": "Configure activity logs.", "/logging-disable": "Disable activity logs.",
        "/antinuke": "Enable anti-nuke protection.", "/antinuke-disable": "Disable anti-nuke.",
        "/sticky": "Set a repeating channel message.", "/sticky-remove": "Remove a sticky.",
    },
    "Utility": {
        "/afk": "Set your AFK status.", "/afk-remove": "Remove your AFK status.",
        "/say": "Send text or a custom-color embed.", "/tax": "Calculate Roblox tax totals.",
        "/ping": "Check latency and status.", "/directory": "Show every command.",
        "/help": "Show the El Paso RP help panel.",
    },
    "Sessions": {
        "/session-start": "Start a session and notify the server.",
        "/session-vote": "Open a vote to auto-start a session.",
        "/session-shutdown": "Shut down the active session.",
        "/session-boost": "Announce a session boost.",
    },
}


def load_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {"guilds": {}}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"guilds": {}}


DATA = load_data()


def guild_data(guild_id: int) -> dict[str, Any]:
    data = DATA.setdefault("guilds", {}).setdefault(
        str(guild_id), {"afk": {}, "warnings": {}, "stickies": {}}
    )
    data.setdefault("session", {"active": False, "required_votes": 0, "voters": []})
    return data


def save_data() -> None:
    DATA_FILE.write_text(json.dumps(DATA, indent=2), encoding="utf-8")


def make_embed(title: str, description: str, colour: discord.Colour = PINK) -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=colour)


def action_error(interaction: discord.Interaction, member: discord.Member) -> str | None:
    if member == interaction.user:
        return "You cannot moderate yourself."
    if member == interaction.guild.owner:
        return "The server owner cannot be moderated."
    if member.top_role >= interaction.user.top_role:
        return "That member's highest role is above or equal to yours."
    if member.top_role >= interaction.guild.me.top_role:
        return "My role must be above that member's highest role."
    return None


class RoleRestrictionError(app_commands.CheckFailure):
    """Raised when a command user is missing the configured staff role."""


def require_role(role_id: int, role_name: str):
    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if role_id <= 0 or not isinstance(member, discord.Member):
            raise RoleRestrictionError(f"The {role_name} role is not configured for this bot yet.")
        if not any(role.id == role_id for role in member.roles):
            raise RoleRestrictionError(f"You need the configured {role_name} role to use this command.")
        return True

    return app_commands.check(predicate)


staff_only = require_role(STAFF_ROLE_ID, "staff")
admin_only = require_role(ADMIN_ROLE_ID, "admin")
session_only = require_role(SESSION_ROLE_ID, "session perms")


def session_embed(title: str, description: str, banner_url: str, colour: discord.Colour = PINK) -> discord.Embed:
    embed = make_embed(title, description, colour)
    if banner_url:
        embed.set_image(url=banner_url)
    return embed


class SessionLinkView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        button = discord.ui.Button(
            label="Join Server", style=discord.ButtonStyle.link,
            url=SERVER_INVITE_URL or "https://discord.com", disabled=not bool(SERVER_INVITE_URL)
        )
        self.add_item(button)


class SessionVoteView(discord.ui.View):
    def __init__(self, guild_id: int, vote_count: int = 0) -> None:
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.vote_button = discord.ui.Button(
            label=f"Vote ({vote_count})", style=discord.ButtonStyle.success,
            custom_id=f"session-vote:{guild_id}"
        )
        self.vote_button.callback = self.cast_vote
        self.add_item(self.vote_button)

    async def cast_vote(self, interaction: discord.Interaction) -> None:
        data = guild_data(self.guild_id)
        session = data["session"]
        if session.get("active"):
            await interaction.response.send_message("A session is already active.", ephemeral=True)
            return
        if session.get("vote_message_id") and interaction.message.id != session["vote_message_id"]:
            await interaction.response.send_message("This vote is no longer active.", ephemeral=True)
            return
        voter_id = str(interaction.user.id)
        voters = session.setdefault("voters", [])
        if voter_id in voters:
            await interaction.response.send_message("You have already voted for this session.", ephemeral=True)
            return
        voters.append(voter_id)
        save_data()
        vote_count = len(voters)
        self.vote_button.label = f"Vote ({vote_count})"
        required_votes = max(1, int(session.get("required_votes", 1)))
        if vote_count >= required_votes and interaction.guild and interaction.channel:
            await interaction.response.defer()
            await interaction.message.edit(view=self)
            await start_session(interaction.guild, interaction.channel)
            await interaction.followup.send("The required votes were reached. The session has started.", ephemeral=True)
            return
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            f"Vote recorded: **{vote_count}/{required_votes}**.", ephemeral=True
        )


async def start_session(guild: discord.Guild, channel: discord.abc.Messageable) -> None:
    session = guild_data(guild.id)["session"]
    if session.get("active"):
        return
    voters = list(session.get("voters", []))
    session.update({"active": True, "required_votes": 0, "voters": [], "vote_message_id": None})
    save_data()
    await channel.send(
        content="@here",
        embed=session_embed(
            "EL PASO RP | Session Started",
            "The roleplay session is now live. Join the server using the button below and be ready to play.",
            SESSION_START_BANNER_URL,
        ),
        view=SessionLinkView(),
        allowed_mentions=discord.AllowedMentions(everyone=True),
    )
    for voter_id in voters:
        try:
            user = await bot.fetch_user(int(voter_id))
            await user.send("The session has started. You will be warned if you do not join the game.")
        except (discord.HTTPException, discord.Forbidden, ValueError):
            continue


def remove_afk_prefix(nickname: str | None) -> str | None:
    if not nickname:
        return nickname
    cleaned = nickname.removeprefix("[AFK] ").removeprefix("[AFK]").strip()
    return cleaned or None


async def set_afk_nickname(member: discord.Member, is_afk: bool) -> None:
    try:
        if is_afk:
            if not member.display_name.startswith("[AFK]"):
                nickname = f"[AFK] {member.display_name}"[:32]
                await member.edit(nick=nickname, reason="AFK status enabled")
        else:
            nickname = remove_afk_prefix(member.nick)
            if member.nick and not nickname:
                nickname = None
            if member.nick != nickname:
                await member.edit(nick=nickname, reason="AFK status removed")
    except (discord.Forbidden, discord.HTTPException):
        pass


async def clear_afk_nickname(member: discord.Member, original_nickname: str | None = None) -> None:
    try:
        nickname = original_nickname if original_nickname is not None else remove_afk_prefix(member.nick)
        if member.nick != nickname:
            await member.edit(nick=nickname, reason="AFK status removed")
    except (discord.Forbidden, discord.HTTPException):
        pass


class ElPasoBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        for guild_id, data in DATA.get("guilds", {}).items():
            session = data.get("session", {})
            if not session.get("active") and session.get("required_votes", 0):
                self.add_view(SessionVoteView(int(guild_id), len(session.get("voters", []))))
        await self.tree.sync()

    async def on_ready(self) -> None:
        await self.change_presence(activity=discord.Game("El Paso RP | /directory"))
        print(f"Online as {self.user} in {len(self.guilds)} server(s)")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self.user and self.user in message.mentions and message.content.strip() in (
            f"<@{self.user.id}>", f"<@!{self.user.id}>"
        ):
            await message.reply(embed=make_embed(
                "EL PASO RP | Mod-Bot",
                "Neon pink moderation online. Use **/directory** to view every command.",
            ))
            return
        if message.guild:
            data = guild_data(message.guild.id)
            afk_users = data.get("afk", {})
            if str(message.author.id) in afk_users:
                afk_users.pop(str(message.author.id))
                original_nickname = data.get("afk_nicknames", {}).pop(str(message.author.id), None)
                save_data()
                if isinstance(message.author, discord.Member):
                    await clear_afk_nickname(message.author, original_nickname)
                await message.reply("Welcome back. Your AFK status has been removed.", delete_after=8)
            mentioned = [member for member in message.mentions if str(member.id) in afk_users]
            if mentioned:
                text = ", ".join(f"**{member.display_name}**: {afk_users[str(member.id)]}" for member in mentioned)
                await message.reply(f"AFK: {text}", delete_after=12)
            sticky = data.get("stickies", {}).get(str(message.channel.id))
            if sticky:
                try:
                    previous = await message.channel.fetch_message(sticky["message_id"])
                    await previous.delete()
                except discord.HTTPException:
                    pass
                try:
                    sent = await message.channel.send(sticky["text"], silent=True)
                    sticky["message_id"] = sent.id
                    save_data()
                except discord.HTTPException:
                    pass
        await self.process_commands(message)

    async def log_event(self, guild: discord.Guild, title: str, text: str) -> None:
        channel_id = guild_data(guild.id).get("log_channel", LOG_CHANNEL_ID)
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel:
            try:
                await channel.send(embed=make_embed(title, text))
            except discord.HTTPException:
                pass

bot = ElPasoBot()


@bot.tree.command(name="ping", description="Check bot latency and status")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(embed=make_embed(
        "EL PASO RP | Online", f"Latency: **{round(bot.latency * 1000)}ms**\nStatus: **Operational**"
    ))


@bot.tree.command(name="directory", description="Show the complete command directory")
async def directory(interaction: discord.Interaction) -> None:
    description = "\n\n".join(
        f"**{category}**\n" + "\n".join(f"`{name}` - {desc}" for name, desc in command_list.items())
        for category, command_list in COMMAND_DIRECTORY.items()
    )
    await interaction.response.send_message(embed=make_embed("EL PASO RP | Command Directory", description))


@bot.tree.command(name="help", description="Show the El Paso RP help panel")
async def help_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(embed=make_embed(
        "El Paso RP Mod-Bot",
        "A neon pink moderation suite for private roleplay servers.\n\nUse **/directory** for the full command list. Moderation commands require the matching Discord permission.",
    ))


@bot.tree.command(name="session-start", description="Start a roleplay session")
@session_only
@app_commands.guild_only()
async def session_start(interaction: discord.Interaction) -> None:
    session = guild_data(interaction.guild_id)["session"]
    if session.get("active"):
        await interaction.response.send_message("A session is already active.", ephemeral=True)
        return
    await interaction.response.defer()
    await start_session(interaction.guild, interaction.channel)
    await interaction.followup.send("Session started.", ephemeral=True)


@bot.tree.command(name="session-vote", description="Open a vote to automatically start a session")
@session_only
@app_commands.guild_only()
@app_commands.describe(required_votes="Votes needed before the session starts automatically")
async def session_vote(
    interaction: discord.Interaction,
    required_votes: app_commands.Range[int, 1, 100],
) -> None:
    session = guild_data(interaction.guild_id)["session"]
    if session.get("active"):
        await interaction.response.send_message("A session is already active.", ephemeral=True)
        return
    session.update({"required_votes": int(required_votes), "voters": []})
    save_data()
    await interaction.response.send_message(
        content="@here",
        embed=session_embed(
            "EL PASO RP | Session Vote",
            f"Vote to start the next roleplay session. The session will start automatically when **{required_votes}** vote(s) are reached.\n\nCurrent votes: **0/{required_votes}**",
            SESSION_VOTE_BANNER_URL,
        ),
        view=SessionVoteView(interaction.guild_id),
        allowed_mentions=discord.AllowedMentions(everyone=True),
    )
    vote_message = await interaction.original_response()
    session["vote_message_id"] = vote_message.id
    save_data()


@bot.tree.command(name="session-shutdown", description="Shut down the active roleplay session")
@session_only
@app_commands.guild_only()
async def session_shutdown(interaction: discord.Interaction) -> None:
    session = guild_data(interaction.guild_id)["session"]
    if not session.get("active"):
        await interaction.response.send_message("There is no active session.", ephemeral=True)
        return
    session.update({"active": False, "required_votes": 0, "voters": [], "vote_message_id": None})
    save_data()
    await interaction.response.send_message(embed=session_embed(
        "EL PASO RP | Session Shutdown",
        "The roleplay session has ended. Thank you for playing.",
        SESSION_SHUTDOWN_BANNER_URL,
    ))


@bot.tree.command(name="session-boost", description="Announce a roleplay session boost")
@session_only
@app_commands.guild_only()
async def session_boost(interaction: discord.Interaction) -> None:
    if not guild_data(interaction.guild_id)["session"].get("active"):
        await interaction.response.send_message("There is no active session to boost.", ephemeral=True)
        return
    await interaction.response.send_message(embed=session_embed(
        "EL PASO RP | Session Boost",
        "The active session needs more players. Join the game and help keep the roleplay moving.",
        SESSION_BOOST_BANNER_URL,
    ))


@bot.tree.command(name="tax", description="Calculate Roblox tax and required charge")
@app_commands.describe(robux="Robux amount")
async def tax(interaction: discord.Interaction, robux: app_commands.Range[int, 1, 2_000_000_000]) -> None:
    received = int(robux * 0.7)
    charge = int((robux / 0.7) + 0.999999)
    await interaction.response.send_message(embed=make_embed(
        "Roblox Tax Calculator",
        f"Payment: **{robux:,} Robux**\nAfter 30% tax: **{received:,} Robux**\nTo receive **{robux:,}**, charge: **{charge:,} Robux**",
    ))


@bot.tree.command(name="say", description="Send a message as the bot")
@staff_only
@app_commands.describe(text="Message content", use_embed="Send as an embed", color="Hex color, e.g. #ff1493")
async def say(interaction: discord.Interaction, text: str, use_embed: bool = False, color: str = "#ff1493") -> None:
    await interaction.response.defer(ephemeral=True)
    if use_embed:
        try:
            colour = discord.Colour(value=int(color.strip().lstrip("#"), 16))
        except ValueError:
            await interaction.followup.send("Use a valid hex color like `#ff1493`.", ephemeral=True)
            return
        message = await interaction.channel.send(embed=discord.Embed(description=text, colour=colour))
    else:
        message = await interaction.channel.send(text)
    await interaction.followup.send(f"Sent message `{message.id}`.", ephemeral=True)


@bot.tree.command(name="afk", description="Set your AFK status")
async def afk(interaction: discord.Interaction, reason: str = "Away") -> None:
    data = guild_data(interaction.guild_id)
    data["afk"][str(interaction.user.id)] = reason[:200]
    save_data()
    if isinstance(interaction.user, discord.Member):
        data.setdefault("afk_nicknames", {})[str(interaction.user.id)] = interaction.user.nick
        await set_afk_nickname(interaction.user, True)
        save_data()
    await interaction.response.send_message(f"AFK enabled: **{reason[:200]}**", ephemeral=True)


@bot.tree.command(name="afk-remove", description="Remove your AFK status")
async def afk_remove(interaction: discord.Interaction) -> None:
    data = guild_data(interaction.guild_id)
    data.get("afk", {}).pop(str(interaction.user.id), None)
    original_nickname = data.get("afk_nicknames", {}).pop(str(interaction.user.id), None)
    save_data()
    if isinstance(interaction.user, discord.Member):
        await clear_afk_nickname(interaction.user, original_nickname)
    await interaction.response.send_message("Your AFK status has been removed.", ephemeral=True)


def permission_command(name: str, description: str, permission: str, access: str = "staff"):
    def decorator(function):
        command = app_commands.Command(name=name, description=description, callback=function)
        command.default_permissions = discord.Permissions(**{permission: True})
        command.add_check(admin_only if access == "admin" else staff_only)
        bot.tree.add_command(command)
        return function
    return decorator


@permission_command("warn", "Warn a member", "moderate_members")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
    issue = action_error(interaction, member)
    if issue:
        await interaction.response.send_message(issue, ephemeral=True)
        return
    records = guild_data(interaction.guild_id).setdefault("warnings", {}).setdefault(str(member.id), [])
    records.append({"reason": reason[:300], "moderator": interaction.user.id})
    save_data()
    await interaction.response.send_message(embed=make_embed("Warning issued", f"{member.mention} now has **{len(records)}** warning(s).\nReason: {reason[:300]}"))
    await bot.log_event(interaction.guild, "Member warned", f"{member} was warned by {interaction.user}: {reason[:300]}")


@permission_command("warnings", "View member warnings", "moderate_members")
async def warnings(interaction: discord.Interaction, member: discord.Member) -> None:
    records = guild_data(interaction.guild_id).get("warnings", {}).get(str(member.id), [])
    text = "\n".join(f"{index}. {record['reason']}" for index, record in enumerate(records, 1)) or "No warnings recorded."
    await interaction.response.send_message(embed=make_embed(f"Warnings | {member}", text), ephemeral=True)


@permission_command("clearwarnings", "Clear member warnings", "moderate_members")
async def clearwarnings(interaction: discord.Interaction, member: discord.Member) -> None:
    guild_data(interaction.guild_id).setdefault("warnings", {}).pop(str(member.id), None)
    save_data()
    await interaction.response.send_message(f"Cleared warnings for {member.mention}.")


@bot.tree.command(name="serverinfo", description="Show server information")
async def serverinfo(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    await interaction.response.send_message(embed=make_embed(
        f"{guild.name} | Server Info",
        f"Owner: {guild.owner.mention if guild.owner else 'Unknown'}\nMembers: **{guild.member_count}**\nChannels: **{len(guild.channels)}**\nRoles: **{len(guild.roles)}**\nCreated: <t:{int(guild.created_at.timestamp())}:D>",
    ))


@bot.tree.command(name="userinfo", description="Show member information")
async def userinfo(interaction: discord.Interaction, member: discord.Member | None = None) -> None:
    member = member or interaction.user
    await interaction.response.send_message(embed=make_embed(
        f"{member.display_name} | User Info",
        f"User: {member.mention}\nID: `{member.id}`\nJoined: <t:{int(member.joined_at.timestamp())}:D>\nAccount created: <t:{int(member.created_at.timestamp())}:D>\nTop role: {member.top_role.mention}",
    ))


@permission_command("purge", "Delete recent messages", "manage_messages")
async def purge(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]) -> None:
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted **{len(deleted)}** message(s).", ephemeral=True)


@permission_command("slowmode", "Set channel slowmode", "manage_channels")
async def slowmode(interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]) -> None:
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"Slowmode set to **{seconds}** seconds.")


@permission_command("lock", "Lock this channel", "manage_channels", "admin")
async def lock(interaction: discord.Interaction) -> None:
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(embed=make_embed("Channel locked", "This channel is now read-only."))


@permission_command("unlock", "Unlock this channel", "manage_channels", "admin")
async def unlock(interaction: discord.Interaction) -> None:
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
    await interaction.response.send_message(embed=make_embed("Channel unlocked", "Chat access has been restored."))


@permission_command("nickname", "Set or clear a member nickname", "manage_nicknames")
async def nickname(interaction: discord.Interaction, member: discord.Member, name: str | None = None) -> None:
    issue = action_error(interaction, member)
    if issue:
        await interaction.response.send_message(issue, ephemeral=True)
        return
    await member.edit(nick=name)
    await interaction.response.send_message(f"Nickname updated for {member.mention}.")


@permission_command("role", "Add or remove a role", "manage_roles", "admin")
@app_commands.describe(action="Choose add or remove")
async def role(interaction: discord.Interaction, member: discord.Member, role: discord.Role, action: str = "add") -> None:
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("My role must be above the role I manage.", ephemeral=True)
        return
    if action.lower() == "remove":
        await member.remove_roles(role)
        verb = "Removed"
        preposition = "from"
    else:
        await member.add_roles(role)
        verb = "Added"
        preposition = "to"
    await interaction.response.send_message(f"{verb} {role.mention} {preposition} {member.mention}.")


@permission_command("kick", "Kick a member", "kick_members")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
    issue = action_error(interaction, member)
    if issue:
        await interaction.response.send_message(issue, ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"Kicked **{member}**. Reason: {reason}")


@permission_command("ban", "Ban a member", "ban_members", "admin")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
    issue = action_error(interaction, member)
    if issue:
        await interaction.response.send_message(issue, ephemeral=True)
        return
    await member.ban(reason=reason, delete_message_seconds=0)
    await interaction.response.send_message(f"Banned **{member}**. Reason: {reason}")


@permission_command("softban", "Softban a member", "ban_members", "admin")
async def softban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
    issue = action_error(interaction, member)
    if issue:
        await interaction.response.send_message(issue, ephemeral=True)
        return
    await member.ban(reason=reason, delete_message_seconds=1)
    await interaction.guild.unban(member, reason="Softban release")
    await interaction.response.send_message(f"Softbanned **{member}**.")


@permission_command("unban", "Unban a user ID", "ban_members", "admin")
async def unban(interaction: discord.Interaction, user_id: str) -> None:
    if not user_id.isdigit():
        await interaction.response.send_message("Provide a numeric Discord user ID.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
    except (discord.NotFound, discord.HTTPException):
        await interaction.response.send_message("That user is not banned or could not be found.", ephemeral=True)
        return
    await interaction.response.send_message(f"Unbanned **{user}**.")


@permission_command("timeout", "Timeout a member", "moderate_members")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 40320], reason: str = "No reason provided") -> None:
    issue = action_error(interaction, member)
    if issue:
        await interaction.response.send_message(issue, ephemeral=True)
        return
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await interaction.response.send_message(f"Timed out {member.mention} for **{minutes} minutes**.")


@permission_command("untimeout", "Remove a timeout", "moderate_members")
async def untimeout(interaction: discord.Interaction, member: discord.Member) -> None:
    await member.timeout(None, reason=f"Removed by {interaction.user}")
    await interaction.response.send_message(f"Removed timeout from {member.mention}.")


@permission_command("logging", "Configure activity logging", "manage_guild", "admin")
async def logging(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    guild_data(interaction.guild_id)["log_channel"] = channel.id
    save_data()
    await interaction.response.send_message(f"Logging enabled in {channel.mention}.")


@permission_command("logging-disable", "Disable activity logging", "manage_guild", "admin")
async def logging_disable(interaction: discord.Interaction) -> None:
    guild_data(interaction.guild_id).pop("log_channel", None)
    save_data()
    await interaction.response.send_message("Activity logging disabled.")


@permission_command("sticky", "Set a repeating channel message", "manage_messages")
async def sticky(interaction: discord.Interaction, text: str) -> None:
    guild_data(interaction.guild_id).setdefault("stickies", {})[str(interaction.channel_id)] = {
        "text": text[:1900], "message_id": interaction.id
    }
    save_data()
    await interaction.response.send_message("Sticky message configured.")


@permission_command("sticky-remove", "Remove a sticky message", "manage_messages")
async def sticky_remove(interaction: discord.Interaction) -> None:
    guild_data(interaction.guild_id).setdefault("stickies", {}).pop(str(interaction.channel_id), None)
    save_data()
    await interaction.response.send_message("Sticky message removed.")


@permission_command("antinuke", "Configure anti-nuke protection", "administrator", "admin")
async def antinuke(interaction: discord.Interaction, alert_channel: discord.TextChannel | None = None) -> None:
    settings = guild_data(interaction.guild_id)
    settings["antinuke"] = True
    if alert_channel:
        settings["antinuke_channel"] = alert_channel.id
    save_data()
    await interaction.response.send_message("Anti-nuke protection enabled with the configured alert channel.")


@permission_command("antinuke-disable", "Disable anti-nuke protection", "administrator", "admin")
async def antinuke_disable(interaction: discord.Interaction) -> None:
    guild_data(interaction.guild_id)["antinuke"] = False
    save_data()
    await interaction.response.send_message("Anti-nuke protection disabled.")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    await bot.log_event(member.guild, "Member joined", f"{member.mention} joined the server.")


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    await bot.log_event(member.guild, "Member left", f"**{member}** left the server.")


@bot.event
async def on_message_delete(message: discord.Message) -> None:
    if message.guild and not message.author.bot:
        await bot.log_event(message.guild, "Message deleted", f"A message by **{message.author}** was deleted in {message.channel.mention}.")


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
    if before.guild and not before.author.bot and before.content != after.content:
        await bot.log_event(before.guild, "Message edited", f"A message by **{before.author}** was edited in {before.channel.mention}.")


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel) -> None:
    await bot.log_event(channel.guild, "Channel created", f"Created {channel.mention if hasattr(channel, 'mention') else channel.name}.")


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel) -> None:
    await bot.log_event(channel.guild, "Channel deleted", f"Deleted **{channel.name}**.")


@bot.event
async def on_guild_role_create(role: discord.Role) -> None:
    await bot.log_event(role.guild, "Role created", f"Created {role.mention}.")


@bot.event
async def on_guild_role_delete(role: discord.Role) -> None:
    await bot.log_event(role.guild, "Role deleted", f"Deleted **{role.name}**.")


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User) -> None:
    await bot.log_event(guild, "Member banned", f"**{user}** was banned.")


@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User) -> None:
    await bot.log_event(guild, "Member unbanned", f"**{user}** was unbanned.")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, RoleRestrictionError):
        text = str(error)
    elif isinstance(error, app_commands.MissingPermissions):
        text = "You do not have permission to use this command."
    else:
        text = "Something went wrong while running that command. Check my permissions and try again."
        print(f"Command error: {error}")
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Set DISCORD_TOKEN before starting the bot.")
    bot.run(TOKEN)