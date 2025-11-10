import json
import os
import aiohttp
import datetime as dt
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import config


# ===== CHECKS =====
try:
    from utils.checks import in_home_guild as _in_home_guild
    def in_home_guild():
        return _in_home_guild()
except Exception:
    def in_home_guild():
        async def pred(interaction: discord.Interaction):
            return interaction.guild and interaction.guild.id in getattr(config, "ALLOWED_GUILDS", [])
        return app_commands.check(pred)


# ====== DATA UTILS ======
def ensure_data_files():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    if not os.path.exists(config.ORDERS_FILE):
        with open(config.ORDERS_FILE, "w") as f:
            json.dump([], f)


def append_order(entry: dict):
    ensure_data_files()
    with open(config.ORDERS_FILE, "r+", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = []
        data.append(entry)
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()


# ===== PAYPAL =====
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
        "detail": {
            "currency_code": currency,
            "note": description,
            "term": "Due on receipt",
            "memo": "Hububba Studios Commission",
        },
        "invoicer": {"name": {"given_name": "Hububba", "surname": "Studios"}},
        "primary_recipients": [{"billing_info": {"email_address": email}}],
        "items": [{
            "name": item_name,
            "quantity": "1",
            "unit_amount": {"currency_code": currency, "value": f"{amount:.2f}"}
        }]
    }

    # Create invoice
    async with session.post(config.PAYPAL_INVOICE_URL, headers=headers, json=body) as r:
        r.raise_for_status()
        inv = await r.json()

    invoice_id = inv.get("id")
    links = {l["rel"]: l["href"] for l in inv.get("links", [])}
    pay_link = links.get("payer_view")

    # Send invoice
    async with session.post(f"{config.PAYPAL_INVOICE_URL}/{invoice_id}/send", headers=headers) as r:
        r.raise_for_status()

    return {"id": invoice_id, "payer_url": pay_link}


# ===== PANEL SYSTEM =====
async def ensure_panel(bot: commands.Bot):
    await bot.wait_until_ready()
    chan = bot.get_channel(config.TICKET_PANEL_CHANNEL_ID)
    if not isinstance(chan, discord.TextChannel):
        return

    async for msg in chan.history(limit=25):
        if msg.author.id == bot.user.id and msg.embeds and msg.embeds[0].title == "Open a Ticket":
            return

    embed = discord.Embed(
        title="Open a Ticket",
        description=(
            "Need support, want to start a commission, or have a complaint?\n"
            "Click a button below to open a ticket. A short form will pop up."
        ),
        color=config.BRAND_COLOR
    )
    embed.set_author(name="Hububba Utilities")

    await chan.send(embed=embed, view=TicketPanelView())


# ===== MODALS / VIEWS =====
class TicketModal(discord.ui.Modal, title="Ticket Details"):
    def __init__(self, ticket_type: str):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.subject = discord.ui.TextInput(label="Subject", max_length=100)
        self.details = discord.ui.TextInput(label="Details", style=discord.TextStyle.long, max_length=1800)
        self.add_item(self.subject)
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return

        cat_name = {
            "support": config.SUPPORT_CATEGORY_NAME,
            "commission": config.COMMISSION_CATEGORY_NAME,
            "complaint": config.COMPLAINT_CATEGORY_NAME
        }.get(self.ticket_type, config.SUPPORT_CATEGORY_NAME)

        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            category = await guild.create_category(cat_name)

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

        log_chan = interaction.client.get_channel(config.LOG_CHANNEL_ID)
        if isinstance(log_chan, discord.TextChannel):
            embed = discord.Embed(
                title=f"New {self.ticket_type.title()} Ticket",
                color=config.BRAND_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="User", value=interaction.user.mention)
            embed.add_field(name="Subject", value=str(self.subject))
            embed.add_field(name="Channel", value=ch.mention)
            await log_chan.send(embed=embed)

        ticket_embed = discord.Embed(
            title=f"{self.ticket_type.title()} Ticket",
            description=f"**Subject:** {self.subject}\n**Details:** {self.details}\n\nStaff will assist soon.",
            color=config.BRAND_COLOR
        )
        await ch.send(interaction.user.mention, embed=ticket_embed)
        await interaction.response.send_message(f"Created {ch.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Support", style=discord.ButtonStyle.primary, emoji="🛠️")
    async def support(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(TicketModal("support"))

    @discord.ui.button(label="Commission", style=discord.ButtonStyle.primary, emoji="💼")
    async def commission(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(TicketModal("commission"))

    @discord.ui.button(label="Complaint", style=discord.ButtonStyle.primary, emoji="📣")
    async def complaint(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(TicketModal("complaint"))


# ===== COG =====
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ensure_data_files()
        bot.loop.create_task(ensure_panel(bot))

    @app_commands.command(name="close", description="Close and archive this ticket.")
    @in_home_guild()
    async def close(self, interaction: discord.Interaction):
        ch = interaction.channel
        guild = interaction.guild
        if not isinstance(ch, discord.TextChannel) or not guild:
            return await interaction.response.send_message("Run this inside a ticket.", ephemeral=True)

        archive_cat = discord.utils.get(guild.categories, name=config.ARCHIVE_CATEGORY_NAME)
        if not archive_cat:
            archive_cat = await guild.create_category(config.ARCHIVE_CATEGORY_NAME)

        await ch.edit(category=archive_cat)
        await ch.set_permissions(guild.default_role, view_channel=False)
        await ch.send("✅ Ticket archived.")

        log_chan = interaction.client.get_channel(config.LOG_CHANNEL_ID)
        if isinstance(log_chan, discord.TextChannel):
            embed = discord.Embed(
                title="Ticket Archived",
                description=f"{ch.mention} archived by {interaction.user.mention}",
                color=config.BRAND_COLOR
            )
            await log_chan.send(embed=embed)

    @app_commands.command(name="invoice", description="Create a PayPal invoice.")
    @in_home_guild()
    async def invoice(self, interaction: discord.Interaction,
                      email: str, amount: float, currency: str = "USD",
                      description: str = "Hububba Commission", item_name: str = "Commission"):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            async with aiohttp.ClientSession() as session:
                token = await get_paypal_token(session)
                inv = await create_and_send_invoice(session, token, email=email, amount=amount,
                                                    currency=currency, description=description,
                                                    item_name=item_name)
        except Exception as e:
            await interaction.followup.send(f"❌ PayPal error: `{e}`", ephemeral=True)
            return

        append_order({
            "id": inv["id"], "email": email, "amount": amount, "currency": currency,
            "description": description, "created": dt.datetime.utcnow().isoformat()
        })

        log_chan = interaction.client.get_channel(config.LOG_CHANNEL_ID)
        if isinstance(log_chan, discord.TextChannel):
            embed = discord.Embed(title="Invoice Created", color=config.BRAND_COLOR)
            embed.add_field(name="ID", value=inv["id"])
            embed.add_field(name="Client", value=email)
            embed.add_field(name="Amount", value=f"{currency} {amount}")
            embed.add_field(name="Pay Link", value=inv["payer_url"], inline=False)
            await log_chan.send(embed=embed)

        await interaction.followup.send(f"✅ Invoice `{inv['id']}` created.\nPay link: {inv['payer_url']}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
