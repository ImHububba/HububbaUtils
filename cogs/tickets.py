import discord
from discord.ext import commands, tasks
import config
import asyncio
import logging

logger = logging.getLogger("bot")

# =====================
# Persistent Ticket View
# =====================

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent view — survives restarts

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.blurple, custom_id="ticket:create")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        existing = discord.utils.get(category.text_channels, name=f"ticket-{user.name.lower().replace(' ', '-')}")
        if existing:
            await interaction.response.send_message(f"❗ You already have a ticket open: {existing.mention}", ephemeral=True)
            return

        channel = await category.create_text_channel(name=f"ticket-{user.name}", overwrites=overwrites)
        await channel.send(f"{user.mention} — thanks for opening a ticket! A staff member will be with you shortly.")
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)
        logger.info(f"🎟️ Created ticket for {user} in {guild.name}")

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket:close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not channel.name.startswith("ticket-"):
            await interaction.response.send_message("⚠️ You can only close this inside a ticket channel.", ephemeral=True)
            return
        await interaction.response.send_message("🕒 Closing ticket in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await channel.delete()
        logger.info(f"🗑️ Closed ticket channel {channel.name}")


# =====================
# Cog Setup
# =====================

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._ensure_panel_task.start()

    def cog_unload(self):
        self._ensure_panel_task.cancel()

    @tasks.loop(count=1)
    async def _ensure_panel_task(self):
        await self.bot.wait_until_ready()
        await self._ensure_panel()

    async def _ensure_panel(self):
        channel = self.bot.get_channel(config.TICKET_PANEL_CHANNEL_ID)
        if not channel:
            logger.error("❌ Ticket panel channel not found.")
            return

        # delete any old bot messages
        async for msg in channel.history(limit=100):
            if msg.author == self.bot.user:
                await msg.delete()

        embed = discord.Embed(
            title="🎟️ Support Tickets",
            description="Need help? Click below to open a ticket.",
            color=discord.Color.blue(),
        )
        view = TicketView()
        await channel.send(embed=embed, view=view)
        logger.info("✅ Ticket panel sent.")

    @_ensure_panel_task.before_loop
    async def before_panel(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    bot.add_view(TicketView())  # <— makes the buttons persistent across restarts
    await bot.add_cog(Tickets(bot))
    logger.info("✅ Loaded Tickets Cog")
