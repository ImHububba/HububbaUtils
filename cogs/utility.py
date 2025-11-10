# cogs/utility.py
import discord
from discord.ext import commands
from discord import app_commands

import config
from utils.checks import in_allowed_guilds, perm_level


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ADMIN: Ping (restricted as per your matrix)
    @app_commands.command(name="ping", description="Pong!")
    @in_allowed_guilds()
    @perm_level("admin")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! `{round(self.bot.latency * 1000)} ms`", ephemeral=True)

    # ADMIN: role IDs helper (kept admin as before)
    @app_commands.command(name="roleids", description="Get all role IDs in this server.")
    @in_allowed_guilds()
    @perm_level("admin")
    async def roleids(self, interaction: discord.Interaction):
        roles = sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True)
        lines = [f"`{r.id}` — {r.name}" for r in roles if r.name != "@everyone"]
        content = "Role IDs:\n" + "\n".join(lines) if lines else "No roles found."
        await interaction.response.send_message(content, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
