import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import os
from datetime import datetime

import config
from utils.checks import in_home_guild, perm_level


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.orders_file = config.ORDERS_FILE

        os.makedirs(os.path.dirname(self.orders_file), exist_ok=True)
        if not os.path.exists(self.orders_file):
            with open(self.orders_file, "w") as f:
                json.dump({}, f, indent=4)

    # ======= BASIC TICKET CREATION =======

    @app_commands.command(name="newticket", description="Create a new commission or support ticket.")
    @in_home_guild()
    async def newticket(self, interaction: discord.Interaction, ticket_type: str, description: str):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="Tickets")
        if not category:
            category = await interaction.guild.create_category("Tickets")

        chan_name = f"{interaction.user.name}-{ticket_type}".replace(" ", "-").lower()
        channel = await interaction.guild.create_text_channel(chan_name, category=category)

        await channel.set_permissions(interaction.guild.default_role, read_messages=False)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)

        await channel.send(
            embed=discord.Embed(
                title=f"🎫 New Ticket — {ticket_type.capitalize()}",
                description=f"Opened by {interaction.user.mention}\n\n**Description:** {description}",
                color=0x5865F2,
            )
        )

        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

        log_chan = self.bot.get_channel(config.LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(f"🟢 New ticket created by {interaction.user.mention} — {channel.mention}")

    # ======= CLOSE / ARCHIVE =======

    @app_commands.command(name="close", description="Close and archive this ticket.")
    @in_home_guild()
    async def close(self, interaction: discord.Interaction):
        chan = interaction.channel
        await interaction.response.defer(ephemeral=True)

        archive_cat = discord.utils.get(interaction.guild.categories, name=config.ARCHIVE_CATEGORY)
        if not archive_cat:
            archive_cat = await interaction.guild.create_category(config.ARCHIVE_CATEGORY)

        await chan.edit(category=archive_cat)
        await chan.send("🔒 This ticket has been archived.")

        log_chan = self.bot.get_channel(config.LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(f"🔒 Ticket archived: {chan.name} by {interaction.user.mention}")

        await interaction.followup.send("✅ Ticket archived successfully.", ephemeral=True)

    # ======= COMMISSION ORDER CREATION =======

    @app_commands.command(name="order", description="Create a commission order and PayPal invoice.")
    @perm_level("admin")
    async def order(self, interaction: discord.Interaction, client: discord.Member, amount: float, description: str):
        await interaction.response.defer(ephemeral=True)

        # Create PayPal invoice
        async with aiohttp.ClientSession() as session:
            token = await self._get_paypal_token(session)
            if not token:
                await interaction.followup.send("❌ Failed to authenticate with PayPal API.", ephemeral=True)
                return

            invoice_url = await self._create_paypal_invoice(session, token, client, amount, description)
            if not invoice_url:
                await interaction.followup.send("❌ Failed to create PayPal invoice.", ephemeral=True)
                return

        order_id = f"ORD-{int(datetime.utcnow().timestamp())}"
        order_data = {
            "id": order_id,
            "client": str(client.id),
            "amount": amount,
            "description": description,
            "invoice_url": invoice_url,
            "status": "Pending",
            "created_at": str(datetime.utcnow())
        }

        self._save_order(order_id, order_data)

        embed = discord.Embed(
            title="🧾 Commission Order Created",
            description=f"**Client:** {client.mention}\n**Amount:** ${amount:.2f}\n**Description:** {description}\n\n[Open Invoice]({invoice_url})",
            color=0x2ECC71,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

        log_chan = self.bot.get_channel(config.LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(embed=embed)

    # ======= VIEW ORDERS =======

    @app_commands.command(name="orders", description="View all current commission orders.")
    @perm_level("admin")
    async def orders(self, interaction: discord.Interaction):
        with open(self.orders_file, "r") as f:
            data = json.load(f)

        if not data:
            await interaction.response.send_message("No orders found.", ephemeral=True)
            return

        embed = discord.Embed(title="📋 Active Orders", color=0x3498DB)
        for order in data.values():
            embed.add_field(
                name=f"{order['id']} — ${order['amount']}",
                value=f"Client: <@{order['client']}>\nStatus: {order['status']}\n[Invoice Link]({order['invoice_url']})",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ======= UTIL FUNCTIONS =======

    def _save_order(self, order_id, data):
        with open(self.orders_file, "r") as f:
            orders = json.load(f)
        orders[order_id] = data
        with open(self.orders_file, "w") as f:
            json.dump(orders, f, indent=4)

    async def _get_paypal_token(self, session: aiohttp.ClientSession):
        auth = aiohttp.BasicAuth(config.PAYPAL_CLIENT_ID, config.PAYPAL_CLIENT_SECRET)
        async with session.post(f"{config.PAYPAL_API_BASE}/v1/oauth2/token", data={"grant_type": "client_credentials"}, auth=auth) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["access_token"]
            return None

    async def _create_paypal_invoice(self, session, token, client, amount, description):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "detail": {
                "invoice_number": f"INV-{int(datetime.utcnow().timestamp())}",
                "currency_code": "USD",
                "note": f"Commission for {client.name}",
                "terms_and_conditions": "Payment due within 7 days."
            },
            "invoicer": {"name": {"given_name": "Hububba Studios"}},
            "primary_recipients": [{"billing_info": {"email_address": f"{client.name}@example.com"}}],
            "items": [{
                "name": description,
                "quantity": "1",
                "unit_amount": {"currency_code": "USD", "value": f"{amount:.2f}"}
            }]
        }

        async with session.post(f"{config.PAYPAL_API_BASE}/v2/invoicing/invoices", headers=headers, json=payload) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return data["href"] if "href" in data else f"https://www.paypal.com/invoice/payerView/details/{data.get('id', '')}"
            return None


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
