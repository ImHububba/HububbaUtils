# main.py
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os

import config
from utils.logger import setup_logger

# Intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True  # required for edit/delete logs

# Bot
bot = commands.Bot(command_prefix="!", intents=intents)

logger = setup_logger(config.LOG_FILE_PATH, config.LOG_MAX_BYTES, config.LOG_BACKUP_COUNT)

@bot.event
async def on_ready():
    # Presence
    await bot.change_presence(
        activity=discord.Game(name=config.BOT_STATUS_TEXT),
        status=discord.Status.online
    )
    logger.info(f"✅ Logged in as {bot.user} ({bot.user.id})")

    # Sync slash commands to the home guild only
    try:
        guild = discord.Object(id=config.GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        logger.info(f"🌿 Synced {len(synced)} application commands to guild {config.GUILD_ID}.")
    except Exception as e:
        logger.exception(f"Failed to sync commands: {e}")

@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    If invited elsewhere, politely inform and leave.
    """
    try:
        text_target = guild.system_channel
        if text_target is None:
            # pick the first text channel we can talk in
            for ch in guild.text_channels:
                perms = ch.permissions_for(guild.me)
                if perms.send_messages:
                    text_target = ch
                    break
        if text_target:
            await text_target.send(
                "Hi! I only function inside **Hububba's Coding world** and will now leave. "
                "Invite me there if needed. ✌️"
            )
    finally:
        # Leave any non-home guild
        if guild.id != config.GUILD_ID:
            await guild.leave()

# Friendly error for failed checks (e.g., wrong guild / missing role)
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    from utils.checks import PermissionDenied
    if isinstance(error, PermissionDenied) or isinstance(error, app_commands.CheckFailure):
        # Send a clear ephemeral message
        try:
            await interaction.response.send_message(str(error), ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(str(error), ephemeral=True)
        return
    # Log others and show a generic message
    logger.exception("Slash command error", exc_info=error)
    msg = "Something went wrong running that command."
    try:
        await interaction.response.send_message(msg, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(msg, ephemeral=True)

async def load_extensions():
    await bot.load_extension("cogs.moderation")
    await bot.load_extension("cogs.utility")
    await bot.load_extension("cogs.autoroles")
    await bot.load_extension("cogs.logging_cog")
    await bot.load_extension("cogs.twitch")

def read_token() -> str:
    token_path = os.path.join(os.path.dirname(__file__), "token.txt")
    if not os.path.exists(token_path):
        raise FileNotFoundError("token.txt not found. Create it and put your bot token on a single line.")
    with open(token_path, "r", encoding="utf-8") as f:
        token = f.read().strip()
    if not token:
        raise ValueError("token.txt is empty.")
    return token

async def main():
    await load_extensions()
    token = read_token()
    await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
