# main.py — Hububba Utils (Final Fixed Slash Command Sync)
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os

import config
from utils.logger import setup_logger

ALLOWED_GUILDS = [config.HUBUBBA_GUILD_ID, config.PROJECT_INFINITE_ID]

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
logger = setup_logger(config.LOG_FILE_PATH, config.LOG_MAX_BYTES, config.LOG_BACKUP_COUNT)


def read_token() -> str:
    token_path = os.path.join(os.path.dirname(__file__), "token.txt")
    if not os.path.exists(token_path):
        raise FileNotFoundError("token.txt not found. Put your bot token on one line.")
    with open(token_path, "r", encoding="utf-8") as f:
        token = f.read().strip().replace("$", "").strip()
    if not token:
        raise ValueError("token.txt is empty or invalid.")
    return token


async def load_extensions():
    extensions = [
        "cogs.moderation",
        "cogs.utility",
        "cogs.autoroles",
        "cogs.logging_cog",
        "cogs.twitch",
        "cogs.tickets",
    ]
    for ext in extensions:
        try:
            if ext in bot.extensions:
                await bot.reload_extension(ext)
            else:
                await bot.load_extension(ext)
            logger.info(f"✅ Loaded extension: {ext}")
        except Exception as e:
            logger.error(f"❌ Failed to load {ext}: {e}")


@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user} ({bot.user.id})")
    await bot.change_presence(activity=discord.Game(name=config.BOT_STATUS_TEXT))

    await load_extensions()

    # Give cogs a second to fully register their app_commands
    await asyncio.sleep(1)

    # Force re-sync commands
    total_synced = 0
    try:
        for guild_id in ALLOWED_GUILDS:
            guild = discord.Object(id=guild_id)
            synced = await bot.tree.sync(guild=guild)
            total_synced += len(synced)
            logger.info(f"🌿 Synced {len(synced)} commands to guild {guild_id}.")
        logger.info(f"✅ Finished syncing {total_synced} total commands across {len(ALLOWED_GUILDS)} guilds.")
    except Exception as e:
        logger.exception(f"❌ Command sync failed: {e}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    from utils.checks import PermissionDenied
    if isinstance(error, (PermissionDenied, app_commands.CheckFailure)):
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


async def main():
    token = read_token()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down cleanly...")
