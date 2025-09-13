# cogs/autoroles.py
import discord
from discord.ext import commands
import config

class AutoRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        role = discord.utils.get(member.guild.roles, name=config.AUTO_ROLE_NAME)
        if role:
            try:
                await member.add_roles(role, reason="Auto-role on join")
                chan = self.bot.get_channel(config.GENERAL_LOGS_CHANNEL_ID)
                if isinstance(chan, discord.TextChannel):
                    await chan.send(f"👋 **Join**: {member.mention} joined, auto-assigned `{role.name}`.")
            except Exception as e:
                chan = self.bot.get_channel(config.BOT_LOGS_CHANNEL_ID)
                if isinstance(chan, discord.TextChannel):
                    await chan.send(f"⚠️ Auto-role failed for {member.mention}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoles(bot))
