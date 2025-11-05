import discord
from discord.ext import commands
import config


class AutoRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Automatically assign the correct default role when a user joins.
        """
        guild_id = member.guild.id

        # Get guild-specific role config
        guild_roles = config.ROLE_MAP.get(guild_id)
        if not guild_roles:
            return  # no config for this guild

        role_to_assign = None

        # Hububba’s Coding World uses role name
        if "AUTO" in guild_roles and isinstance(guild_roles["AUTO"], str):
            role_to_assign = discord.utils.get(member.guild.roles, name=guild_roles["AUTO"])

        # Project Infinite uses role ID
        elif "AUTO" in guild_roles and isinstance(guild_roles["AUTO"], int):
            role_to_assign = member.guild.get_role(guild_roles["AUTO"])

        if role_to_assign:
            try:
                await member.add_roles(role_to_assign, reason="Auto role on join")
                print(f"✅ Gave {role_to_assign.name} to {member} in {member.guild.name}")
            except discord.Forbidden:
                print(f"⚠️ Missing permission to assign {role_to_assign} in {member.guild.name}")
            except Exception as e:
                print(f"❌ Failed to assign auto role in {member.guild.name}: {e}")
        else:
            print(f"⚠️ No matching auto role found for {member.guild.name}")

    # Manual command if needed
    @commands.command(name="autorole")
    @commands.has_permissions(administrator=True)
    async def give_autorole(self, ctx, member: discord.Member = None):
        """
        Manually give the autorole to a member (admin only).
        """
        member = member or ctx.author
        guild_id = ctx.guild.id

        guild_roles = config.ROLE_MAP.get(guild_id)
        if not guild_roles:
            return await ctx.send("⚠️ No autorole configured for this server.")

        role_to_assign = None
        if isinstance(guild_roles["AUTO"], str):
            role_to_assign = discord.utils.get(ctx.guild.roles, name=guild_roles["AUTO"])
        else:
            role_to_assign = ctx.guild.get_role(guild_roles["AUTO"])

        if not role_to_assign:
            return await ctx.send("⚠️ Could not find the autorole in this server.")

        await member.add_roles(role_to_assign)
        await ctx.send(f"✅ Gave {role_to_assign.mention} to {member.mention}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoles(bot))
