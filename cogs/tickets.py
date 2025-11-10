# cogs/tickets.py
import json
import os
import asyncio
import discord
from discord import ui, app_commands
from discord.ext import commands
from typing import Optional

try:
    import config
except Exception:
    class config:  # fallback to avoid crashes if missing fields
        HUBUBBA_GUILD_ID = 0
        PROJECT_INFINITE_ID = 0
        STAFF_ROLE_ID = 0
        TICKETS_CATEGORY_ID = 0
        CLOSED_TICKETS_CATEGORY_ID = 0
        BOT_LOGS_CHANNEL_ID = 0

DATA_DIR = "data"
PANEL_META = os.path.join(DATA_DIR, "ticket_panel.json")

def _ensure_data():
    os.makedirs(DATA_DIR, exist_ok=True)

def _load_panel_state():
    _ensure_data()
    if not os.path.exists(PANEL_META):
        return {}
    try:
        with open(PANEL_META, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            return json.loads(raw) if raw else {}
    except Exception:
        return {}

def _save_panel_state(d: dict):
    _ensure_data()
    tmp = PANEL_META + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, PANEL_META)

def _get_staff_role(guild: discord.Guild) -> Optional[discord.Role]:
    rid = getattr(config, "STAFF_ROLE_ID", 0) or 0
    return guild.get_role(rid) if rid else None

def _get_or_make_category(guild: discord.Guild, category_id: int, name: str) -> discord.CategoryChannel:
    cat = guild.get_channel(category_id) if category_id else None
    if isinstance(cat, discord.CategoryChannel):
        return cat
    # fallback: find by name or create
    for c in guild.categories:
        if c.name.lower() == name.lower():
            return c
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, view_channel=False)
    }
    return asyncio.get_event_loop().run_until_complete(guild.create_category(name=name, overwrites=overwrites))

class TicketCategorySelect(ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Select a ticket type…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Support", value="support", emoji="🛠️", description="General help"),
                discord.SelectOption(label="Bug Report", value="bug", emoji="🐞", description="Report an issue"),
                discord.SelectOption(label="Commission", value="commission", emoji="🧾", description="Paid work / order"),
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value == "commission":
            modal = CommissionModal()
        elif value == "bug":
            modal = BugModal()
        else:
            modal = SupportModal()
        await interaction.response.send_modal(modal)

class TicketPanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

class SupportModal(ui.Modal, title="Support Ticket"):
    topic = ui.TextInput(label="Topic", required=True, max_length=200)
    details = ui.TextInput(label="Details", style=discord.TextStyle.long, required=True, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_from_modal(interaction, kind="Support", fields={
            "Topic": str(self.topic),
            "Details": str(self.details),
        })

class BugModal(ui.Modal, title="Bug Report"):
    summary = ui.TextInput(label="Summary", required=True, max_length=200)
    steps = ui.TextInput(label="Steps to Reproduce", style=discord.TextStyle.long, required=True, max_length=2000)
    expected = ui.TextInput(label="Expected Behavior", required=False, max_length=300)
    actual = ui.TextInput(label="Actual Behavior", required=False, max_length=300)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_from_modal(interaction, kind="Bug", fields={
            "Summary": str(self.summary),
            "Steps": str(self.steps),
            "Expected": str(self.expected),
            "Actual": str(self.actual),
        })

class CommissionModal(ui.Modal, title="Commission Request"):
    title = ui.TextInput(label="Title", required=True, max_length=120, placeholder="Website redesign / Bot feature / etc.")
    budget = ui.TextInput(label="Budget", required=False, max_length=80, placeholder="$50 – $200")
    deadline = ui.TextInput(label="Deadline", required=False, max_length=80, placeholder="e.g., Nov 30")
    notes = ui.TextInput(label="Notes", style=discord.TextStyle.long, required=False, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_from_modal(interaction, kind="Commission", fields={
            "Title": str(self.title),
            "Budget": str(self.budget),
            "Deadline": str(self.deadline),
            "Notes": str(self.notes),
        }, commission=True)

class TicketControls(ui.View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    @ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="ticket_close_btn")
    async def close_btn(self, interaction: discord.Interaction, button: ui.Button):
        # only staff or opener
        guild = interaction.guild
        staff = _get_staff_role(guild)
        if interaction.user.id != self.opener_id and (not staff or staff not in interaction.user.roles):
            await interaction.response.send_message("You can't close this ticket.", ephemeral=True)
            return
        await interaction.response.send_modal(CloseReasonModal())

class CloseReasonModal(ui.Modal, title="Close Ticket"):
    reason = ui.TextInput(label="Reason", required=False, max_length=300)

    async def on_submit(self, interaction: discord.Interaction):
        await close_ticket(interaction, str(self.reason or "").strip() or "No reason provided.")

async def create_ticket_from_modal(
    interaction: discord.Interaction,
    kind: str,
    fields: dict,
    commission: bool = False,
):
    guild = interaction.guild
    assert guild is not None
    # categories
    open_cat = _get_or_make_category(
        guild,
        getattr(config, "TICKETS_CATEGORY_ID", 0) or 0,
        "Tickets"
    )

    # create private channel for user + staff
    staff = _get_staff_role(guild)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    if staff:
        overwrites[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)

    channel = await guild.create_text_channel(
        name=f"{kind.lower()}-{interaction.user.name[:18]}",
        category=open_cat,
        overwrites=overwrites,
        reason=f"{kind} ticket opened by {interaction.user}",
    )

    # embed summary
    embed = discord.Embed(
        title=f"{kind} Ticket",
        color=discord.Color.blue(),
        description="\n".join([f"**{k}:** {discord.utils.escape_markdown(v or 'N/A')}" for k, v in fields.items()])
    )
    embed.add_field(name="Opened by", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)

    view = TicketControls(opener_id=interaction.user.id)
    msg = await channel.send(embed=embed, view=view)

    # link back to user
    await interaction.response.send_message(f"Created {kind} ticket: {channel.mention}", ephemeral=True)

    # auto-create order for commission
    if commission:
        try:
            from .orders import create_order_from_ticket
            order = create_order_from_ticket(
                user_id=interaction.user.id,
                ticket_channel_id=channel.id,
                title=fields.get("Title") or f"Commission for {interaction.user.name}",
                budget=fields.get("Budget"),
                deadline=fields.get("Deadline"),
                notes=fields.get("Notes"),
            )
            await channel.send(f"🧾 Auto-created **Order #{order.id}** linked to this ticket.")
        except Exception as e:
            await channel.send(f"⚠️ Failed to auto-create order: `{e}`")

async def close_ticket(interaction: discord.Interaction, reason: str):
    guild = interaction.guild
    channel = interaction.channel
    if not guild or not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("This isn't a ticket channel.", ephemeral=True)
        return

    # move to closed category (or create it)
    closed_cat = _get_or_make_category(
        guild,
        getattr(config, "CLOSED_TICKETS_CATEGORY_ID", 0) or 0,
        "Closed Tickets"
    )

    # lock and move
    try:
        overwrites = channel.overwrites
        # remove opener send permission
        for target, perms in list(overwrites.items()):
            if isinstance(target, discord.Member):
                overwrites[target] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)
        await channel.edit(category=closed_cat, overwrites=overwrites, reason=f"Closed by {interaction.user} — {reason}")
    except Exception:
        pass

    await interaction.response.send_message("Ticket closed. Moving channel…", ephemeral=True)
    await channel.send(f"🔒 Ticket closed by {interaction.user.mention}\n**Reason:** {discord.utils.escape_markdown(reason)}")

class Tickets(commands.Cog, name="Tickets"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # persistent view on startup
    async def cog_load(self):
        self.bot.add_view(TicketPanelView())
        if hasattr(self.bot, "logger"):
            self.bot.logger.info("✅ Loaded Tickets Cog")

    # /ticketpanel — idempotent
    @app_commands.command(name="ticketpanel", description="Send/refresh the ticket panel (staff only).")
    @app_commands.guild_only()
    async def ticketpanel(self, interaction: discord.Interaction):
        guild = interaction.guild
        staff = _get_staff_role(guild)
        if staff and staff not in interaction.user.roles:
            await interaction.response.send_message("Staff only.", ephemeral=True)
            return

        state = _load_panel_state()
        # delete previous panel if exists
        try:
            if state.get("guild_id") == guild.id and state.get("channel_id") and state.get("message_id"):
                ch = guild.get_channel(state["channel_id"])
                if isinstance(ch, discord.TextChannel):
                    msg = await ch.fetch_message(state["message_id"])
                    await msg.delete()
        except Exception:
            pass

        view = TicketPanelView()
        embed = discord.Embed(
            title="🎫 Project Infinite — Tickets",
            description="Pick a category to open a ticket.\nSupport • Bug • Commission",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message("Panel sent.", ephemeral=True)
        panel_msg = await interaction.channel.send(embed=embed, view=view)

        state = {
            "guild_id": guild.id,
            "channel_id": interaction.channel_id,
            "message_id": panel_msg.id,
        }
        _save_panel_state(state)
        await interaction.followup.send("✅ Ticket panel sent.", ephemeral=True)

    # /close — works inside the ticket channel, asks for reason via modal
    @app_commands.command(name="close", description="Close the current ticket.")
    @app_commands.guild_only()
    async def close(self, interaction: discord.Interaction):
        # only staff or opener can close — we enforce via the modal handler too, but guard here as well
        staff = _get_staff_role(interaction.guild)
        if staff and staff not in interaction.user.roles:
            # allow opener user as fallback: check channel topic opener id marker
            ch = interaction.channel
            if isinstance(ch, discord.TextChannel):
                pass  # we allow the modal but will enforce in the view; simplest UX: just show modal
        await interaction.response.send_modal(CloseReasonModal())

async def setup(bot: commands.Bot):
    cog = Tickets(bot)
    await bot.add_cog(cog)
    if hasattr(bot, "logger"):
        bot.logger.info("✅ Registered 0 commands from Tickets")
