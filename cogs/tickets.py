import json
import os
import aiohttp
import datetime as dt
import random
import discord
from discord.ext import commands
from discord import app_commands
import config


# ===== Checks =====
try:
    from utils.checks import in_home_guild as _in_home_guild
    def in_home_guild():
        return _in_home_guild()
except Exception:
    def in_home_guild():
        async def pred(interaction: discord.Interaction):
            return interaction.guild and interaction.guild.id in getattr(config, "ALLOWED_GUILDS", [])
        return app_commands.check(pred)


# ===== Data Utils =====
def ensure_data():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    if not os.path.exists(config.ORDERS_FILE):
        with open(config.ORDERS_FILE, "w") as f:
            json.dump([], f)


def load_orders():
    ensure_data()
    with open(config.ORDERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def save_orders(data):
    ensure_data()
    with open(config.ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def generate_order_id():
    return f"C{random.randint(1000,9999)}"


# ===== PayPal =====
async def get_paypal_token(session: aiohttp.ClientSession):
    auth = aiohttp.BasicAuth(config.PAYPAL_CLIENT_ID, config.PAYPAL_SECRET)
    form = {"grant_type": "client_credentials"}
    async with session.post(config.PAYPAL_OAUTH_URL, data=form, auth=auth) as r:
        r.raise_for_status()
        data = await r.json()
        return data["access_token"]


async def create_and_send_invoice(session, token, *, email, amount, currency, description, item_name):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "detail": {"currency_code": currency, "note": description, "memo": "Hububba Studios Commission"},
        "invoicer": {"name": {"given_name": "Hububba", "surname": "Studios"}},
        "primary_recipients": [{"billing_info": {"email_address": email}}],
        "items": [{
            "name": item_name,
            "quantity": "1",
            "unit_amount": {"currency_code": currency, "value": f"{amount:.2f}"}
        }]
    }

    async with session.post(config.PAYPAL_INVOICE_URL, headers=headers, json=body) as r:
        r.raise_for_status()
        inv = await r.json()

    invoice_id = inv.get("id")
    links = {l["rel"]: l["href"] for l in inv.get("links", [])}
    pay_link = links.get("payer_view")

    await session.post(f"{config.PAYPAL_INVOICE_URL}/{invoice_id}/send", headers=headers)
    return {"id": invoice_id, "payer_url": pay_link}


# ===== Panel Setup =====
async def ensure_panel(bot: commands.Bot):
    await bot.wait_until_ready()
    chan = bot.get_channel(config.TICKET_PANEL_CHANNEL_ID)
    if not isinstance(chan, discord.TextChannel):
        return
    try:
        await chan.purge(limit=None)
    except Exception as e:
        print(f"[WARN] Failed to purge: {e}")

    embed = discord.Embed(
        title="🎟️ Open a Ticket",
        description="Need help, a commission, or have a complaint?\n\nPick an option below to start.",
        color=config.BRAND_COLOR
    )
    embed.set_author(name="Hububba Utilities", icon_url=bot.user.display_avatar.url)
    embed.set_footer(text="Hububba Studios ∞")

    await chan.send(embed=embed, view=TicketPanelView())
    print("✅ Ticket panel refreshed and sent.")


# ===== Modals =====
class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        self.ticket_type = ticket_type
        title = f"{ticket_type.title()} Ticket Form"
        super().__init__(title=title, timeout=None)

        # Different questions depending on type
        if ticket_type == "support":
            self.q1 = discord.ui.TextInput(label="What's the issue?", max_length=200)
            self.q2 = discord.ui.TextInput(label="What have you tried?", style=discord.TextStyle.long, required=False)
        elif ticket_type == "complaint":
            self.q1 = discord.ui.TextInput(label="Who or what is this about?", max_length=200)
            self.q2 = discord.ui.TextInput(label="Describe the situation", style=discord.TextStyle.long)
        else:  # commission
            self.q1 = discord.ui.TextInput(label="What would you like commissioned?", max_length=200)
            self.q2 = discord.ui.TextInput(label="Additional details, deadline, or budget?", style=discord.TextStyle.long)

        self.add_item(self.q1)
        self.add_item(self.q2)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return

        category_name = {
            "support": config.SUPPORT_CATEGORY_NAME,
            "commission": config.COMMISSION_CATEGORY_NAME,
            "complaint": config.COMPLAINT_CATEGORY_NAME
        }[self.ticket_type]

        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        ch = await guild.create_text_channel(
            name=f"{self.ticket_type}-{interaction.user.name}".replace(" ", "-"),
            category=category,
            overwrites=overwrites
        )

        # Handle commissions → create order
        if self.ticket_type == "commission":
            order_id = generate_order_id()
            orders = load_orders()
            new_order = {
                "id": order_id,
                "client": str(interaction.user),
                "channel_id": ch.id,
                "status": "OPEN",
                "description": str(self.q1),
                "notes": str(self.q2),
                "assigned_to": None,
                "created_at": dt.datetime.utcnow().isoformat()
            }
            orders.append(new_order)
            save_orders(orders)

            embed = discord.Embed(title=f"🧾 Order {order_id} Created", color=config.BRAND_COLOR)
            embed.add_field(name="Client", value=interaction.user.mention)
            embed.add_field(name="Status", value="OPEN")
            embed.add_field(name="Details", value=f"{self.q1}\n{self.q2}")
            await ch.send(embed=embed)

            log = interaction.client.get_channel(config.LOG_CHANNEL_ID)
            if isinstance(log, discord.TextChannel):
                await log.send(embed=embed)

        else:
            embed = discord.Embed(
                title=f"{self.ticket_type.title()} Ticket Created",
                description=f"**Question:** {self.q1}\n**Details:** {self.q2}",
                color=config.BRAND_COLOR
            )
            await ch.send(embed=embed)

        await interaction.response.send_message(f"✅ Created {ch.mention}", ephemeral=True)


# ===== Panel Buttons =====
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Support", style=discord.ButtonStyle.primary, emoji="🛠️")
    async def support(self, i: discord.Interaction, _):
        await i.response.send_modal(TicketModal("support"))

    @discord.ui.button(label="Commission", style=discord.ButtonStyle.success, emoji="💼")
    async def commission(self, i: discord.Interaction, _):
        await i.response.send_modal(TicketModal("commission"))

    @discord.ui.button(label="Complaint", style=discord.ButtonStyle.danger, emoji="📣")
    async def complaint(self, i: discord.Interaction, _):
        await i.response.send_modal(TicketModal("complaint"))


# ===== Cog =====
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ensure_data()
        bot.loop.create_task(ensure_panel(bot))

    # ---- TICKET CLOSE ----
    @app_commands.command(name="close", description="Close and archive this ticket.")
    @in_home_guild()
    async def close(self, interaction: discord.Interaction):
        ch = interaction.channel
        guild = interaction.guild
        if not isinstance(ch, discord.TextChannel) or not guild:
            return await interaction.response.send_message("Use this inside a ticket.", ephemeral=True)

        archive_cat = discord.utils.get(guild.categories, name=config.ARCHIVE_CATEGORY_NAME)
        if not archive_cat:
            archive_cat = await guild.create_category(config.ARCHIVE_CATEGORY_NAME)

        await ch.edit(category=archive_cat)
        await ch.set_permissions(guild.default_role, view_channel=False)
        await ch.send("✅ Ticket archived.")

        # Update any linked order
        orders = load_orders()
        for o in orders:
            if o.get("channel_id") == ch.id:
                o["status"] = "CLOSED"
        save_orders(orders)

    # ---- ORDER LIST ----
    @app_commands.command(name="order_list", description="List all orders.")
    @in_home_guild()
    async def order_list(self, interaction: discord.Interaction, status: str = "all"):
        orders = load_orders()
        filtered = [o for o in orders if status.lower() == "all" or o["status"].lower() == status.lower()]
        if not filtered:
            return await interaction.response.send_message("No orders found.", ephemeral=True)

        embed = discord.Embed(title="📦 Orders", color=config.BRAND_COLOR)
        for o in filtered[:10]:
            embed.add_field(
                name=f"{o['id']} ({o['status']})",
                value=f"Client: {o['client']}\nChannel: <#{o['channel_id']}>\nCreated: {o['created_at'][:16]}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---- ORDER UPDATE ----
    @app_commands.command(name="order_update", description="Update an order status or notes.")
    @in_home_guild()
    async def order_update(self, interaction: discord.Interaction, order_id: str, field: str, value: str):
        orders = load_orders()
        found = False
        for o in orders:
            if o["id"] == order_id:
                o[field] = value
                found = True
        save_orders(orders)

        if not found:
            await interaction.response.send_message(f"Order `{order_id}` not found.", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ Updated `{order_id}` — set `{field}` to `{value}`.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
