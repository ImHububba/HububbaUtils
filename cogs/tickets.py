# cogs/tickets.py
import discord
from discord.ext import commands
from discord import app_commands
import json, os, aiohttp
import config

# ===============================
# CONFIG / CONSTANTS
# ===============================
ORDERS_FILE = config.ORDERS_FILE
LOG_CHANNEL_ID = config.LOG_CHANNEL_ID
TICKET_PANEL_CHANNEL_ID = config.TICKET_PANEL_CHANNEL_ID
ARCHIVE_CATEGORY = config.ARCHIVE_CATEGORY

PAYPAL_CLIENT_ID = "YOUR_PAYPAL_CLIENT_ID_HERE"
PAYPAL_SECRET = "YOUR_PAYPAL_SECRET_HERE"
PAYPAL_API = "https://api-m.sandbox.paypal.com"  # switch to live when ready


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
        if not os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, "w") as f:
                json.dump({}, f)

    # ===============================
    # AUTO TICKET PANEL ON STARTUP
    # ===============================
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        panel_channel = self.bot.get_channel(TICKET_PANEL_CHANNEL_ID)
        if not panel_channel:
            print("⚠️ Ticket panel channel not found. Check TICKET_PANEL_CHANNEL_ID.")
            return

        async for msg in panel_channel.history(limit=10):
            if msg.author == self.bot.user and msg.embeds and "Create a Ticket" in (msg.embeds[0].title or ""):
                print("✅ Ticket panel already exists.")
                return

        embed = discord.Embed(
            title="🎫 Create a Ticket",
            description="Need help, have a commission request, or need support?\nClick below to open a private ticket.",
            color=discord.Color.blue(),
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket"))
        await panel_channel.send(embed=embed, view=view)
        print("✅ Ticket panel sent.")

    # ===============================
    # BUTTON INTERACTION HANDLER
    # ===============================
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return
        if interaction.data.get("custom_id") != "open_ticket":
            return

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        if category is None:
            category = await guild.create_category(name="Tickets")

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{interaction.user.name.lower()}")
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket: {existing.mention}", ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}", category=category, overwrites=overwrites
        )

        await ticket_channel.send(
            f"{interaction.user.mention}, thank you for reaching out! Please describe your issue or commission request below."
        )
        await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)

        log_chan = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(f"🎫 **Ticket Opened:** {interaction.user.mention} — {ticket_channel.mention}")

    # ===============================
    # /close TICKET COMMAND
    # ===============================
    @app_commands.command(name="close", description="Close the current ticket and archive it.")
    async def close(self, interaction: discord.Interaction):
        chan = interaction.channel
        if not isinstance(chan, discord.TextChannel) or not chan.name.startswith("ticket-"):
            await interaction.response.send_message("❌ This isn't a ticket channel.", ephemeral=True)
            return

        archive_cat = discord.utils.get(interaction.guild.categories, name=ARCHIVE_CATEGORY)
        if archive_cat is None:
            archive_cat = await interaction.guild.create_category(ARCHIVE_CATEGORY)

        await chan.edit(category=archive_cat, reason="Ticket closed")
        await chan.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message(f"✅ Ticket archived to {archive_cat.name}.", ephemeral=True)

        log_chan = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(f"📦 **Ticket Closed:** {chan.name} by {interaction.user.mention}")

    # ===============================
    # /order CREATE COMMISSION ORDER
    # ===============================
    @app_commands.command(name="order", description="Create a commission order and generate a PayPal invoice.")
    async def order(self, interaction: discord.Interaction, client_name: str, amount: float, description: str):
        await interaction.response.defer(ephemeral=True)
        order_id = f"ORD-{len(self._load_orders()) + 1:04d}"

        invoice_url = await self._create_paypal_invoice(order_id, client_name, amount, description)
        self._save_order(order_id, client_name, amount, description, invoice_url)

        await interaction.followup.send(
            f"✅ **Order Created:** `{order_id}` for **${amount:.2f}**\n📜 Description: {description}\n💰 [PayPal Invoice]({invoice_url})",
            ephemeral=True,
        )

        log_chan = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(f"💼 **Order Created:** `{order_id}` — {client_name} (${amount:.2f})")

    # ===============================
    # HELPER: LOAD/SAVE ORDERS
    # ===============================
    def _load_orders(self):
        with open(ORDERS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def _save_order(self, order_id, client, amount, desc, invoice_url):
        data = self._load_orders()
        data[order_id] = {
            "client": client,
            "amount": amount,
            "desc": desc,
            "invoice_url": invoice_url,
        }
        with open(ORDERS_FILE, "w") as f:
            json.dump(data, f, indent=4)

    # ===============================
    # PAYPAL INVOICE GENERATION
    # ===============================
    async def _create_paypal_invoice(self, order_id, client_name, amount, description):
        """Generate invoice via PayPal REST API"""
        async with aiohttp.ClientSession() as session:
            # Obtain access token
            auth = aiohttp.BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_SECRET)
            async with session.post(f"{PAYPAL_API}/v1/oauth2/token", auth=auth, data={"grant_type": "client_credentials"}) as resp:
                data = await resp.json()
                access_token = data.get("access_token")

            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            invoice_payload = {
                "detail": {"invoice_number": order_id, "currency_code": "USD", "note": "Commission Payment"},
                "invoicer": {"name": {"given_name": "Hububba Studios"}},
                "primary_recipients": [{"billing_info": {"name": {"given_name": client_name}}}],
                "items": [{"name": description, "quantity": "1", "unit_amount": {"currency_code": "USD", "value": f"{amount:.2f}"}}],
            }
            async with session.post(f"{PAYPAL_API}/v2/invoicing/invoices", headers=headers, json=invoice_payload) as resp:
                invoice_data = await resp.json()
                return invoice_data.get("href", "https://paypal.com/invoice/notfound")


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
    print("✅ Loaded Tickets Cog")
