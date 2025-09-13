# cogs/logging_cog.py
import discord
from discord.ext import commands
import traceback

import config

class LoggingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Message deletion
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return
        chan = self.bot.get_channel(config.GENERAL_LOGS_CHANNEL_ID)
        if isinstance(chan, discord.TextChannel):
            author = f"{message.author} ({message.author.id})"
            content = message.content[:1500] if message.content else "*no content*"
            await chan.send(f"🗑️ **Message Deleted** in {message.channel.mention} by {author}\n>>> {content}")

    # Message edit
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.guild is None or before.author.bot:
            return
        if before.content == after.content:
            return
        chan = self.bot.get_channel(config.GENERAL_LOGS_CHANNEL_ID)
        if isinstance(chan, discord.TextChannel):
            author = f"{before.author} ({before.author.id})"
            b = before.content[:800] if before.content else "*no content*"
            a = after.content[:800] if after.content else "*no content*"
            await chan.send(
                f"✏️ **Message Edited** in {before.channel.mention} by {author}\n"
                f"**Before:**\n>>> {b}\n**After:**\n>>> {a}"
            )

    # Slash command usage
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        chan = self.bot.get_channel(config.BOT_LOGS_CHANNEL_ID)
        if isinstance(chan, discord.TextChannel):
            user = interaction.user
            where = interaction.channel.mention if interaction.channel else "DM"
            await chan.send(f"✅ **Command**: `/{command.name}` by {user.mention} in {where}")

    # Fallback for text commands (we're slash-only, but just in case)
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        chan = self.bot.get_channel(config.BOT_LOGS_CHANNEL_ID)
        if isinstance(chan, discord.TextChannel):
            tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            await chan.send(f"❌ **Command Error** in {ctx.channel.mention if ctx.channel else 'DM'}: ```py\n{tb[:1900]}\n```")

    # Member join/leave logs, plus welcome message
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Log to General Logs
        gl = self.bot.get_channel(config.GENERAL_LOGS_CHANNEL_ID)
        if isinstance(gl, discord.TextChannel):
            await gl.send(f"➕ **Member Joined**: {member.mention} (`{member}` | `{member.id}`)")
        # ✅ Welcome message to the dedicated welcome channel
        wc = self.bot.get_channel(config.WELCOME_CHANNEL_ID)
        if isinstance(wc, discord.TextChannel):
            await wc.send(f"👋 Welcome to the server, {member.mention}! Glad to have you here.")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        gl = self.bot.get_channel(config.GENERAL_LOGS_CHANNEL_ID)
        if isinstance(gl, discord.TextChannel):
            await gl.send(f"➖ **Member Left**: `{member}` (`{member.id}`)")

async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingCog(bot))
