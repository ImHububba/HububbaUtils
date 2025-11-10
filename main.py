# main.py — Hububba Utils (Patched Original)
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os

import config
from utils.logger import setup_logger

# ===== ALLOWED GUILDS =====
ALLOWED_GUILDS = [config.HUBUBBA_GUILD_ID, config.PROJECT_INFINITE_ID]

# ===== INTENTS =====
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True  # Needed for logging edits/deletions

# ===== BOT =====
bot = commands.Bot(command_prefix="!", intents=intents)
logger = setup_logger(config.LOG_FILE_PATH, config.LOG_MAX_BYTES, config.LOG_BACKUP_COUNT)


@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Game(name=config.BOT_STATUS_TEXT),
        status=discord.Status.online
    )
    logger.info(f"✅ Logged in as {bot.user} ({bot.user.id})")

    # ===== Re-sync commands =====
    try:
        total_synced = 0
        for guild_id in ALLOWED_GUILDS:
            guild = discord.Object(id=guild_id)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            total_synced += len(synced)
            logger.info(f"🌿 Synced {len(synced)} commands to guild {guild_id}.")
        logger.info(f"✅ Finished syncing to {len(ALLOWED_GUILDS)} guilds ({total_synced} total commands).")
    except Exception as e:
        logger.exception(f"❌ Failed to sync commands: {e}")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Politely leave unauthorized guilds."""
    if guild.id not in ALLOWED_GUILDS:
        try:
            target = guild.system_channel
            if target is None:
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        target = ch
                        break
            if target:
                await target.send(
                    "👋 Hey there! I only function inside **Hububba’s Coding World** and **Project Infinite ∞**, "
                    "so I’ll be leaving now. ✌️"
                )
        finally:
            await guild.leave()
    else:
        logger.info(f"✅ Joined authorized guild: {guild.name} ({guild.id})")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    from utils.checks import PermissionDenied

    if isinstance(error, PermissionDenied) or isinstance(error, app_commands.CheckFailure):
        try:
            await interaction.response.send_message(str(error), ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(str(error), ephemeral=True)
        return

    logger.exception("Slash command error", exc_info=error)
    msg = "Something went wrong running that command."
    try:
        await interaction.response.send_message(msg, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(msg, ephemeral=True)


async def load_extensions():
    """Load all core and custom cogs."""
    extensions = [
        "cogs.moderation",
        "cogs.utility",
        "cogs.autoroles",
        "cogs.logging_cog",
        "cogs.twitch",
        "cogs.tickets",  # ✅ Tickets last for panel refresh
    ]

    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    for ext in extensions:
        try:
            await bot.load_extension(ext)
            logger.info(f"✅ Loaded extension: {ext}")
        except Exception as e:
            logger.error(f"❌ Failed to load {ext}: {e}")


def read_token() -> str:
    """Read token from token.txt (and remove any trailing junk)."""
    token_path = os.path.join(os.path.dirname(__file__), "token.txt")
    if not os.path.exists(token_path):
        raise FileNotFoundError("token.txt not found. Put your bot token on one line.")
    with open(token_path, "r", encoding="utf-8") as f:
        token = f.read().strip()
    # Fix any trailing $ or whitespace characters
    token = token.replace("$", "").strip()
    if not token:
        raise ValueError("token.txt is empty or invalid.")
    return token


async def main():
    await load_extensions()
    token = read_token()
    await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down cleanly...")
