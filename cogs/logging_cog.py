import discord
from discord.ext import commands
import traceback
import config


class LoggingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_channel(self, guild_id: int, key: str) -> discord.TextChannel | None:
        guild_config = config.LOG_CHANNELS.get(guild_id)
        if not guild_config:
            return None
        chan_id = guild_config.get(key)
        return self.bot.get_channel(chan_id)

    # 🗑️ Message deletion
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        chan = self.get_channel(message.guild.id, "GENERAL")
        if not chan:
            return
        author = f"{message.author} ({message.author.id})"
        content = message.content[:1500] if message.content else "*no content*"
        await chan.send(f"🗑️ **Message Deleted** in {message.channel.mention} by {author}\n>>> {content}")

    # ✏️ Message edit
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        chan = self.get_channel(before.guild.id, "GENERAL")
        if not chan:
            return
        author = f"{before.author} ({before.author.id})"
        b = before.content[:800] if before.content else "*no content*"
        a = after.content[:800] if after.content else "*no content*"
        await chan.send(
            f"✏️ **Message Edited** in {before.channel.mention} by {author}\n"
            f"**Before:**\n>>> {b}\n**After:**\n>>> {a}"
        )

    # ✅ Slash command usage
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        if not interaction.guild:
            return
        chan = self.get_channel(interaction.guild.id, "BOT")
        if not chan:
            return
        user = interaction.user
        where = interaction.channel.mention if interaction.channel else "DM"
        await chan.send(f"✅ **Command**: `/{command.name}` by {user.mention} in {where}")

    # ❌ Command error fallback
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if not ctx.guild:
            return
        chan = self.get_channel(ctx.guild.id, "BOT")
        if not chan:
            return
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        await chan.send(f"❌ **Command Error** in {ctx.channel.mention if ctx.channel else 'DM'}: ```py\n{tb[:1900]}\n```")

    # 👋 Member join
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        gl = self.get_channel(member.guild.id, "GENERAL")
        if gl:
            await gl.send(f"➕ **Member Joined**: {member.mention} (`{member}` | `{member.id}`)")
        wc = self.get_channel(member.guild.id, "WELCOME")
        if wc:
            await wc.send(f"👋 Welcome to the server, {member.mention}! Glad to have you here.")

    # 👋 Member leave
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        gl = self.get_channel(member.guild.id, "GENERAL")
        if gl:
            await gl.send(f"➖ **Member Left**: `{member}` (`{member.id}`)")


async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingCog(bot))
