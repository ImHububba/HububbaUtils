import discord
from discord.ext import commands
import json
import os
import config
import asyncio

ORDERS_FILE = config.ORDERS_FILE


class TicketCategoryView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="💬 Support", style=discord.ButtonStyle.primary, custom_id="support")
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "Support Tickets", "Support")

    @discord.ui.button(label="🧾 Commission", style=discord.ButtonStyle.success, custom_id="commission")
    async def commission_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "Commission Tickets", "Commission")

    @discord.ui.button(label="⚠️ Complaint", style=discord.ButtonStyle.danger, custom_id="complaint")
    async def complaint_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "Complaint Tickets", "Complaint")

    async def create_ticket(self, interaction: discord.Interaction, category_name: str, ticket_type: str):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)

        existing = discord.utils.get(guild.text_channels, name=f"{interaction.user.name.lower()}-{ticket_type.lower()}")
        if existing:
            await interaction.response.send_message(f"You already have an open {ticket_type} ticket: {existing.mention}", ephemeral=True)
            return

        channel = await guild.create_text_channel(
            f"{interaction.user.name}-{ticket_type}",
            category=category,
            topic=f"{ticket_type} ticket for {interaction.user.display_name}",
            permission_synced=False
        )
        await channel.set_permissions(interaction.user, view_channel=True, send_messages=True)
        await channel.set_permissions(guild.default_role, view_channel=False)

        embed = discord.Embed(
            title=f"{ticket_type} Ticket",
            description=f"{interaction.user.mention} please answer the following questions to help us assist you.",
            color=config.BRAND_COLOR
        )
        await channel.send(embed=embed)

        if ticket_type == "Commission":
            await self.create_order(channel, interaction.user)

        await interaction.response.send_message(f"✅ {ticket_type} ticket created: {channel.mention}", ephemeral=True)

    async def create_order(self, channel: discord.TextChannel, user: discord.User):
        if not os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, "w") as f:
                json.dump([], f)

        with open(ORDERS_FILE, "r") as f:
            orders = json.load(f)

        order_id = len(orders) + 1
        new_order = {
            "id": order_id,
            "client": str(user.id),
            "status": "Open",
            "notes": "",
            "ticket_channel": channel.id
        }
        orders.append(new_order)

        with open(ORDERS_FILE, "w") as f:
            json.dump(orders, f, indent=4)

        embed = discord.Embed(
            title=f"Commission Ticket",
            description=(
                f"Opened by {user.mention}\n\n"
                f"**Order** #{order_id}\n"
                f"Use `/close` to archive when done."
            ),
            color=config.BRAND_COLOR
        )
        await channel.send(embed=embed)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        if hasattr(self.bot, "_panel_sent"):
            return
        await asyncio.sleep(3)
        channel = self.bot.get_channel(config.TICKET_PANEL_CHANNEL_ID)
        if not channel:
            print("⚠️ Ticket panel channel not found.")
            return

        try:
            await channel.purge(limit=50)
            embed = discord.Embed(
                title="🎫 Project Infinite Ticket Panel",
                description="Select a category below to open a ticket:\n"
                            "💬 Support • 🧾 Commission • ⚠️ Complaint",
                color=config.BRAND_COLOR
            )
            view = TicketCategoryView(self.bot)
            await channel.send(embed=embed, view=view)
            self.bot._panel_sent = True
            print("✅ Ticket panel sent.")
        except Exception as e:
            print(f"⚠️ Failed to send ticket panel: {e}")

    @commands.hybrid_command(name="close", description="Close the current ticket")
    async def close(self, ctx: commands.Context):
        channel = ctx.channel
        if not any(x in channel.name for x in ["support", "commission", "complaint"]):
            await ctx.send("❌ This is not a ticket channel.", delete_after=5)
            return

        archive_category = discord.utils.get(ctx.guild.categories, name=config.ARCHIVE_CATEGORY_NAME)
        if not archive_category:
            archive_category = await ctx.guild.create_category(config.ARCHIVE_CATEGORY_NAME)

        await channel.edit(category=archive_category, reason="Ticket closed")
        await ctx.send("✅ Ticket closed and archived.")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
