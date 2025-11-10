# cogs/tickets.py
import csv
import os
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict

import discord
from discord import app_commands
from discord.ext import commands

# --- Safe config access with fallbacks ---
import config

def cfg(name: str, default=None):
    return getattr(config, name, default)

# Required/used config entries (with safe defaults)
PANEL_CHANNEL_ID       = int(str(cfg("TICKET_PANEL_CHANNEL_ID", "0")) or "0")
LOG_CHANNEL_ID         = int(str(cfg("LOG_CHANNEL_ID", "0")) or "0")

SUPPORT_CATEGORY_NAME   = cfg("SUPPORT_CATEGORY_NAME", "Support")
COMMISSION_CATEGORY_NAME= cfg("COMMISSION_CATEGORY_NAME", "Commissions")
COMPLAINT_CATEGORY_NAME = cfg("COMPLAINT_CATEGORY_NAME", "Complaints")
ARCHIVE_CATEGORY_NAME   = cfg("ARCHIVE_CATEGORY_NAME", "Ticket Archive")

ORDERS_FILE             = cfg("ORDERS_FILE", os.path.join(os.path.dirname(__file__), "..", "orders.csv"))

# PayPal config (expects in config.py)
PAYPAL_CLIENT_ID        = cfg("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET    = cfg("PAYPAL_CLIENT_SECRET", "")
PAYPAL_ENV              = (cfg("PAYPAL_ENV", "sandbox") or "sandbox").lower()  # "live" | "sandbox"

PAYPAL_BASE = "https://api-m.sandbox.paypal.com" if PAYPAL_ENV != "live" else "https://api-m.paypal.com"


# =========================================
# Utilities
# =========================================

def ensure_orders_csv():
    path = os.path.abspath(ORDERS_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "order_id","type","status","created_at","user_id","user_name",
                "ticket_channel_id","details","budget","deadline","notes"
            ])
    return path

def next_order_id() -> str:
    path = ensure_orders_csv()
    last_num = 0
    with open(path, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                num = int(str(row["order_id"]).replace("#", "").strip())
                last_num = max(last_num, num)
            except Exception:
                pass
    return f"#{last_num + 1:04d}"

def append_order(row: Dict[str, str]):
    path = ensure_orders_csv()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            row.get("order_id",""),
            row.get("type",""),
            row.get("status",""),
            row.get("created_at",""),
            row.get("user_id",""),
            row.get("user_name",""),
            row.get("ticket_channel_id",""),
            row.get("details",""),
            row.get("budget",""),
            row.get("deadline",""),
            row.get("notes",""),
        ])

def load_orders() -> List[Dict[str,str]]:
    path = ensure_orders_csv()
    out = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append(row)
    return out

def save_orders(rows: List[Dict[str,str]]):
    path = ensure_orders_csv()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "order_id","type","status","created_at","user_id","user_name",
            "ticket_channel_id","details","budget","deadline","notes"
        ])
        for row in rows:
            w.writerow([
                row.get("order_id",""),
                row.get("type",""),
                row.get("status",""),
                row.get("created_at",""),
                row.get("user_id",""),
                row.get("user_name",""),
                row.get("ticket_channel_id",""),
                row.get("details",""),
                row.get("budget",""),
                row.get("deadline",""),
                row.get("notes",""),
            ])

async def log(bot: commands.Bot, guild: discord.Guild, text: str, embed: Optional[discord.Embed]=None):
    if LOG_CHANNEL_ID:
        ch = bot.get_channel(LOG_CHANNEL_ID) or (guild and guild.get_channel(LOG_CHANNEL_ID))
        if ch:
            try:
                if embed:
                    await ch.send(text, embed=embed)
                else:
                    await ch.send(text)
            except Exception:
                pass


# =========================================
# PayPal helpers
# =========================================
async def paypal_get_token(session) -> Optional[str]:
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        return None
    token_url = f"{PAYPAL_BASE}/v1/oauth2/token"
    auth = discord.http.BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
    data = {"grant_type": "client_credentials"}

    async with session.post(token_url, data=data, auth=auth) as resp:
        if resp.status == 200:
            j = await resp.json()
            return j.get("access_token")
        return None

async def paypal_create_and_send_invoice(session, access_token: str, *, amount: float, currency: str, payer_email: Optional[str], memo: str) -> Optional[str]:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    # Create draft invoice
    create_url = f"{PAYPAL_BASE}/v2/invoicing/invoices"
    body = {
        "detail": {
            "currency_code": currency,
            "note": memo[:2000],
            "term": "Due upon receipt"
        },
        "invoicer": {},
        "primary_recipients": [{"billing_info": {"email_address": payer_email}}] if payer_email else [],
        "items": [{
            "name": "Service",
            "quantity": "1",
            "unit_amount": {"currency_code": currency, "value": f"{amount:.2f}"}
        }]
    }
    async with session.post(create_url, headers=headers, data=json.dumps(body)) as r1:
        if r1.status not in (201, 200):
            return None
        data1 = await r1.json()
        invoice_id = data1.get("id")
        if not invoice_id:
            return None
    # Send invoice
    send_url = f"{PAYPAL_BASE}/v2/invoicing/invoices/{invoice_id}/send"
    async with session.post(send_url, headers=headers) as r2:
        if r2.status not in (202, 200):
            return None
    return invoice_id


# =========================================
# Panel UI
# =========================================

HUBUBBA_PURPLE = discord.Color(0x9b59b6)

class TicketPanelView(discord.ui.View):
    def __init__(self, tickets_cog: "Tickets", timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.cog = tickets_cog

    @discord.ui.button(label="Support", style=discord.ButtonStyle.primary, emoji="🛠️", custom_id="panel_support")
    async def support_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SupportModal(self.cog))

    @discord.ui.button(label="Commission", style=discord.ButtonStyle.success, emoji="🧾", custom_id="panel_commission")
    async def commission_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CommissionModal(self.cog))

    @discord.ui.button(label="Complaint", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="panel_complaint")
    async def complaint_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ComplaintModal(self.cog))


class SupportModal(discord.ui.Modal, title="New Support Ticket"):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

        self.issue = discord.ui.TextInput(
            label="Describe the issue",
            placeholder="What’s broken or not working?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.urgency = discord.ui.TextInput(
            label="Urgency (Low / Medium / High)",
            placeholder="e.g., Medium",
            required=True,
            max_length=20
        )
        self.add_item(self.issue)
        self.add_item(self.urgency)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.open_ticket(
            interaction=interaction,
            kind="Support",
            details=self.issue.value,
            extras={"urgency": self.urgency.value}
        )


class ComplaintModal(discord.ui.Modal, title="New Complaint Ticket"):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

        self.issue = discord.ui.TextInput(
            label="What’s the complaint?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.proof = discord.ui.TextInput(
            label="Links / Proof (optional)",
            required=False,
            max_length=500
        )
        self.add_item(self.issue)
        self.add_item(self.proof)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.open_ticket(
            interaction=interaction,
            kind="Complaint",
            details=self.issue.value,
            extras={"proof": self.proof.value}
        )


class CommissionModal(discord.ui.Modal, title="New Commission Ticket"):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

        self.project = discord.ui.TextInput(
            label="Project / What do you need?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.budget = discord.ui.TextInput(
            label="Budget (USD)",
            placeholder="e.g., 50-150",
            required=False,
            max_length=50
        )
        self.deadline = discord.ui.TextInput(
            label="Deadline (optional)",
            placeholder="YYYY-MM-DD or 'ASAP'",
            required=False,
            max_length=50
        )
        self.notes = discord.ui.TextInput(
            label="Extra notes (optional)",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        self.add_item(self.project)
        self.add_item(self.budget)
        self.add_item(self.deadline)
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        # Auto-create order for commissions
        order_id = next_order_id()
        append_order({
            "order_id": order_id,
            "type": "Commission",
            "status": "Open",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": str(interaction.user.id),
            "user_name": str(interaction.user),
            "ticket_channel_id": "",
            "details": self.project.value,
            "budget": self.budget.value,
            "deadline": self.deadline.value,
            "notes": self.notes.value,
        })
        await self.cog.open_ticket(
            interaction=interaction,
            kind="Commission",
            details=f"{self.project.value}\n\nBudget: {self.budget.value or 'N/A'}\nDeadline: {self.deadline.value or 'N/A'}\nNotes: {self.notes.value or 'None'}",
            extras={"order_id": order_id}
        )


# =========================================
# Order Update Modal
# =========================================
class OrderUpdateModal(discord.ui.Modal, title="Update Order"):
    def __init__(self, order_id: str):
        super().__init__(timeout=None)
        self.order_id = order_id

        self.status = discord.ui.TextInput(
            label="Status",
            placeholder="Open / Looking Into / In Progress / On Hold / Completed / Canceled",
            required=True,
            max_length=40
        )
        self.notes = discord.ui.TextInput(
            label="Notes (optional)",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.status)
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        rows = load_orders()
        hit = False
        for r in rows:
            if r.get("order_id") == self.order_id:
                r["status"] = self.status.value.strip()
                if self.notes.value:
                    existing = r.get("notes","")
                    r["notes"] = (existing + "\n" if existing else "") + f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {self.notes.value}"
                hit = True
                break
        save_orders(rows)

        msg = f"Order **{self.order_id}** updated." if hit else f"Order **{self.order_id}** not found."
        await interaction.response.send_message(msg, ephemeral=True)


# =========================================
# The Cog
# =========================================
class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._panel_task: Optional[asyncio.Task] = None

    async def _ensure_panel(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)  # tiny delay so channels cache
        guilds = [g for g in self.bot.guilds if g is not None]

        for g in guilds:
            if not PANEL_CHANNEL_ID:
                continue
            ch = self.bot.get_channel(PANEL_CHANNEL_ID) or g.get_channel(PANEL_CHANNEL_ID)
            if not isinstance(ch, discord.TextChannel):
                continue

            # Purge EVERYTHING every boot, then send panel
            try:
                await ch.purge(limit=1000)
            except Exception:
                pass

            embed = discord.Embed(
                title="🎟️ Open a Ticket",
                description=(
                    "Choose a ticket type below:\n"
                    "• **Support** – help with bugs/issues.\n"
                    "• **Commission** – paid work; creates an order.\n"
                    "• **Complaint** – report a problem/person.\n\n"
                    "__**Note:**__ Opening a commission **auto-creates an Order** marked **Open**."
                ),
                color=HUBUBBA_PURPLE
            )
            embed.set_footer(text="Hububba Studios • Project Infinite ∞")

            view = TicketPanelView(self)
            await ch.send(embed=embed, view=view)
            print("✅ Ticket panel sent.")

    async def cog_load(self):
        # schedule panel refresh on boot
        self._panel_task = asyncio.create_task(self._ensure_panel())

    async def open_ticket(self, interaction: discord.Interaction, *, kind: str, details: str, extras: Optional[Dict]=None):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Not in a guild.", ephemeral=True); return

        # Find/create category
        cat_name = {
            "Support": SUPPORT_CATEGORY_NAME,
            "Commission": COMMISSION_CATEGORY_NAME,
            "Complaint": COMPLAINT_CATEGORY_NAME,
        }.get(kind, SUPPORT_CATEGORY_NAME)

        category = discord.utils.get(guild.categories, name=cat_name)
        if category is None:
            category = await guild.create_category(cat_name, reason="Ticket system: autocreate")

        # Create channel
        safe_name = f"{kind.lower()}-{interaction.user.name}".replace(" ", "-")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        ch = await guild.create_text_channel(safe_name, category=category, overwrites=overwrites, reason=f"{kind} ticket")

        # If commission with order_id, bind it to the channel
        order_id = (extras or {}).get("order_id")
        if order_id:
            rows = load_orders()
            for r in rows:
                if r.get("order_id") == order_id:
                    r["ticket_channel_id"] = str(ch.id)
                    break
            save_orders(rows)

        # Post first message in the ticket
        embed = discord.Embed(
            title=f"{kind} Ticket",
            description=details,
            color=HUBUBBA_PURPLE
        )
        embed.add_field(name="Opened by", value=f"{interaction.user.mention}", inline=True)
        if order_id:
            embed.add_field(name="Order", value=order_id, inline=True)
        embed.set_footer(text="Use /close to archive when done.")
        await ch.send(content=f"{interaction.user.mention}", embed=embed)

        await interaction.response.send_message(f"Created {kind} ticket: {ch.mention}", ephemeral=True)

        # Log
        await log(self.bot, guild, f"**{kind}** ticket opened by {interaction.user.mention} → {ch.mention}")

    # =====================================
    # Slash commands
    # =====================================
    tickets = app_commands.Group(name="tickets", description="Ticket admin")

    @app_commands.command(name="close", description="Close this ticket and move it to the archive.")
    async def close(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Run this in a ticket channel.", ephemeral=True)
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Not in a guild.", ephemeral=True)
            return

        archive_cat = discord.utils.get(guild.categories, name=ARCHIVE_CATEGORY_NAME)
        if archive_cat is None:
            archive_cat = await guild.create_category(ARCHIVE_CATEGORY_NAME, reason="Ticket system: autocreate archive")

        try:
            await interaction.channel.edit(category=archive_cat, reason=f"Ticket closed by {interaction.user}")
            await interaction.response.send_message("Ticket archived.", ephemeral=True)
            await log(self.bot, guild, f"Ticket archived: {interaction.channel.mention} by {interaction.user.mention}")
        except Exception as e:
            await interaction.response.send_message(f"Failed to archive: {e}", ephemeral=True)

    # Orders
    orders = app_commands.Group(name="order", description="Order management")

    @orders.command(name="list", description="List recent orders (optionally filter by status).")
    @app_commands.describe(status="Optional status filter, e.g., Open, In Progress, Completed")
    async def order_list(self, interaction: discord.Interaction, status: Optional[str] = None):
        rows = load_orders()
        if status:
            rows = [r for r in rows if r.get("status","").lower() == status.lower()]

        rows = sorted(rows, key=lambda r: r.get("created_at",""), reverse=True)[:10]
        if not rows:
            await interaction.response.send_message("No orders found.", ephemeral=True)
            return

        embed = discord.Embed(title="Recent Orders", color=HUBUBBA_PURPLE)
        for r in rows:
            embed.add_field(
                name=f"{r.get('order_id')} • {r.get('type')} • {r.get('status')}",
                value=(
                    f"User: <@{r.get('user_id')}> • Opened: {r.get('created_at')}\n"
                    f"Budget: {r.get('budget') or 'N/A'} • Deadline: {r.get('deadline') or 'N/A'}\n"
                    f"Notes: {(r.get('notes') or '—')[:200]}"
                ),
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @orders.command(name="update", description="Update an order by ID.")
    @app_commands.describe(order_id="Order ID like #0001")
    async def order_update(self, interaction: discord.Interaction, order_id: str):
        await interaction.response.send_modal(OrderUpdateModal(order_id))

    # Invoices
    invoice = app_commands.Group(name="invoice", description="Invoices")

    @invoice.command(name="create", description="Create & send a PayPal invoice.")
    @app_commands.describe(amount="Amount in USD", description="Memo/description", payer_email="Recipient email")
    async def invoice_create(self, interaction: discord.Interaction, amount: float, description: str, payer_email: Optional[str] = None, currency: str = "USD"):
        await interaction.response.defer(ephemeral=True)
        if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
            await interaction.followup.send("PayPal is not configured.", ephemeral=True)
            return

        # Use discord's aiohttp session via bot.http
        session = self.bot.http._HTTPClient__session  # type: ignore (we just need an aiohttp.ClientSession)
        token = await paypal_get_token(session)
        if not token:
            await interaction.followup.send("Failed to authenticate with PayPal.", ephemeral=True)
            return

        invoice_id = await paypal_create_and_send_invoice(
            session, token,
            amount=amount, currency=currency, payer_email=payer_email, memo=description
        )
        if not invoice_id:
            await interaction.followup.send("Failed to create/send invoice.", ephemeral=True)
            return

        await interaction.followup.send(f"✅ Invoice **{invoice_id}** created and sent.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
    print("✅ Loaded Tickets Cog")
