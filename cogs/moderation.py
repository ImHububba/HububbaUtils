import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

import config
from utils.checks import in_allowed_guilds, perm_level


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # STAFF: Kick
    @app_commands.command(name="kick", description="Kick a user with optional reason.")
    @in_allowed_guilds()
    @perm_level("staff")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.kick(reason=reason)
            await interaction.followup.send(f"👢 Kicked {member} — {reason}", ephemeral=True)
            await self._log_general(interaction.guild.id, f"👢 **Kick**: {member.mention} by {interaction.user.mention}\nReason: {reason}")
        except Exception as e:
            await interaction.followup.send(f"Kick failed: {e}", ephemeral=True)

    # STAFF: Purge
    @app_commands.command(name="purge", description="Bulk delete the last N messages in this channel.")
    @in_allowed_guilds()
    @perm_level("staff")
    async def purge(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 1000]):
        await interaction.response.defer(ephemeral=True)
        try:
            chan = interaction.channel
            if not isinstance(chan, discord.TextChannel):
                await interaction.followup.send("This command must be used in a text channel.", ephemeral=True)
                return
            deleted = await chan.purge(limit=amount, reason=f"Purged by {interaction.user}")
            await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
            await self._log_general(interaction.guild.id, f"🧹 **Purge**: {interaction.user.mention} deleted {len(deleted)} in {chan.mention}")
        except Exception as e:
            await interaction.followup.send(f"Purge failed: {e}", ephemeral=True)

    # STAFF: Timeout
    @app_commands.command(name="timeout", description="Timeout (mute) a user for N minutes (1-10080).")
    @in_allowed_guilds()
    @perm_level("staff")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 10080], reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)
        try:
            dur = timedelta(minutes=minutes)
            await member.timeout(dur, reason=reason)
            await interaction.followup.send(f"⏳ Timed out {member} for {minutes} minutes — {reason}", ephemeral=True)
            await self._log_general(interaction.guild.id, f"⏳ **Timeout**: {member.mention} for {minutes}m by {interaction.user.mention}\nReason: {reason}")
        except Exception as e:
            await interaction.followup.send(f"Timeout failed: {e}", ephemeral=True)

    # STAFF: Untimeout
    @app_commands.command(name="untimeout", description="Remove timeout from a user.")
    @in_allowed_guilds()
    @perm_level("staff")
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.timeout(None)
            await interaction.followup.send(f"✅ Removed timeout for {member}", ephemeral=True)
            await self._log_general(interaction.guild.id, f"✅ **Un-timeout**: {member.mention} by {interaction.user.mention}")
        except Exception as e:
            await interaction.followup.send(f"Untimeout failed: {e}", ephemeral=True)

    # ADMIN: Lock
    @app_commands.command(name="lock", description="Lock the current channel (deny @everyone sending).")
    @in_allowed_guilds()
    @perm_level("admin")
    async def lock(self, interaction: discord.Interaction, reason: str = "Channel locked"):
        await interaction.response.defer(ephemeral=True)
        chan = interaction.channel
        if not isinstance(chan, discord.TextChannel):
            await interaction.followup.send("This command must be used in a text channel.", ephemeral=True)
            return
        try:
            everyone = interaction.guild.default_role
            overwrites = chan.overwrites_for(everyone)
            overwrites.send_messages = False
            await chan.set_permissions(everyone, overwrite=overwrites, reason=reason)
            await interaction.followup.send(f"🔒 Locked {chan.mention}.", ephemeral=True)
            await self._log_general(interaction.guild.id, f"🔒 **Lock**: {chan.mention} by {interaction.user.mention}\nReason: {reason}")
        except Exception as e:
            await interaction.followup.send(f"Lock failed: {e}", ephemeral=True)

    # ADMIN: Unlock
    @app_commands.command(name="unlock", description="Unlock the current channel (restore @everyone sending).")
    @in_allowed_guilds()
    @perm_level("admin")
    async def unlock(self, interaction: discord.Interaction, reason: str = "Channel unlocked"):
        await interaction.response.defer(ephemeral=True)
        chan = interaction.channel
        if not isinstance(chan, discord.TextChannel):
            await interaction.followup.send("This command must be used in a text channel.", ephemeral=True)
            return
        try:
            everyone = interaction.guild.default_role
            overwrites = chan.overwrites_for(everyone)
            overwrites.send_messages = None
            await chan.set_permissions(everyone, overwrite=overwrites, reason=reason)
            await interaction.followup.send(f"🔓 Unlocked {chan.mention}.", ephemeral=True)
            await self._log_general(interaction.guild.id, f"🔓 **Unlock**: {chan.mention} by {interaction.user.mention}\nReason: {reason}")
        except Exception as e:
            await interaction.followup.send(f"Unlock failed: {e}", ephemeral=True)

    # ADMIN: Ban
    @app_commands.command(name="ban", description="Ban a user with optional reason.")
    @in_allowed_guilds()
    @perm_level("admin")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.ban(reason=reason, delete_message_days=0)
            await interaction.followup.send(f"🔨 Banned {member} — {reason}", ephemeral=True)
            await self._log_general(interaction.guild.id, f"🔨 **Ban**: {member.mention} by {interaction.user.mention}\nReason: {reason}")
        except Exception as e:
            await interaction.followup.send(f"Ban failed: {e}", ephemeral=True)

    # ==========================
    # LOGGING HANDLER
    # ==========================
    async def _log_general(self, guild_id: int, message: str):
        log_channel = None
        guild_logs = config.LOG_CHANNELS.get(guild_id)
        if guild_logs:
            log_channel = self.bot.get_channel(guild_logs.get("GENERAL"))

        if isinstance(log_channel, discord.TextChannel):
            await log_channel.send(message)
        else:
            print(f"[WARN] No GENERAL log channel found for guild {guild_id}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
