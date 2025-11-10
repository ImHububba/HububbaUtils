import discord
from discord import app_commands
from discord.ext import commands
import json, os
from datetime import datetime

ORDERS_FILE = "data/orders.json"

# === Utility ===
def load_orders():
    if not os.path.exists(ORDERS_FILE):
        os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
        with open(ORDERS_FILE, "w") as f:
            json.dump({}, f)
    with open(ORDERS_FILE, "r") as f:
        return json.load(f)

def save_orders(data):
    with open(ORDERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_order_id():
    orders = load_orders()
    if not orders:
        return "0001"
    next_id = len(orders) + 1
    return f"{next_id:04d}"

# === Order Cog ===
class Orders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ===================================================
    # /order create
    # ===================================================
    @app_commands.command(name="order_create", description="Create a new order manually")
    async def order_create(self, interaction: discord.Interaction,
                           client: discord.User,
                           title: str,
                           budget: str,
                           deadline: str,
                           notes: str):
        orders = load_orders()
        order_id = generate_order_id()

        orders[order_id] = {
            "client": client.id,
            "title": title,
            "budget": budget,
            "deadline": deadline,
            "notes": notes,
            "status": "Open",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_by": interaction.user.id
        }

        save_orders(orders)

        embed = discord.Embed(
            title=f"🧾 New Order Created — #{order_id}",
            color=discord.Color.purple()
        )
        embed.add_field(name="Client", value=client.mention, inline=True)
        embed.add_field(name="Budget", value=budget, inline=True)
        embed.add_field(name="Deadline", value=deadline, inline=True)
        embed.add_field(name="Notes", value=notes, inline=False)
        embed.set_footer(text=f"Created by {interaction.user}")

        await interaction.response.send_message(embed=embed)
        await client.send(f"✅ Your order **#{order_id}** has been created!")

    # ===================================================
    # /order update
    # ===================================================
    @app_commands.command(name="order_update", description="Update order status")
    async def order_update(self, interaction: discord.Interaction, order_id: str, status: str):
        orders = load_orders()
        if order_id not in orders:
            await interaction.response.send_message(f"❌ Order {order_id} not found.", ephemeral=True)
            return

        orders[order_id]["status"] = status
        save_orders(orders)
        await interaction.response.send_message(f"✅ Order {order_id} status updated to **{status}**.", ephemeral=True)

    # ===================================================
    # /order notes
    # ===================================================
    @app_commands.command(name="order_notes", description="View notes of an order")
    async def order_notes(self, interaction: discord.Interaction, order_id: str):
        orders = load_orders()
        if order_id not in orders:
            await interaction.response.send_message(f"❌ Order {order_id} not found.", ephemeral=True)
            return

        notes = orders[order_id].get("notes", "No notes found.")
        embed = discord.Embed(
            title=f"📝 Notes for Order #{order_id}",
            description=notes,
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ===================================================
    # /order manage
    # ===================================================
    @app_commands.command(name="order_manage", description="Staff management panel for an order")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def order_manage(self, interaction: discord.Interaction, order_id: str):
        orders = load_orders()
        if order_id not in orders:
            await interaction.response.send_message(f"❌ Order {order_id} not found.", ephemeral=True)
            return

        order = orders[order_id]
        embed = discord.Embed(
            title=f"⚙️ Manage Order #{order_id}",
            color=discord.Color.purple()
        )
        embed.add_field(name="Client", value=f"<@{order['client']}>", inline=True)
        embed.add_field(name="Budget", value=order['budget'], inline=True)
        embed.add_field(name="Deadline", value=order['deadline'], inline=True)
        embed.add_field(name="Status", value=order['status'], inline=True)
        embed.add_field(name="Notes", value=order['notes'][:500], inline=False)
        embed.set_footer(text=f"Created by <@{order['created_by']}> • {order['created_at']}")

        view = ManageOrderView(order_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ===================================================
# INTERACTIVE PANEL
# ===================================================
class ManageOrderView(discord.ui.View):
    def __init__(self, order_id):
        super().__init__(timeout=None)
        self.order_id = order_id

    # --- Status Dropdown ---
    @discord.ui.select(
        placeholder="Change order status...",
        options=[
            discord.SelectOption(label="Open", emoji="🟢"),
            discord.SelectOption(label="In Progress", emoji="🟡"),
            discord.SelectOption(label="Completed", emoji="✅"),
            discord.SelectOption(label="Cancelled", emoji="❌")
        ]
    )
    async def status_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        orders = load_orders()
        if self.order_id not in orders:
            await interaction.response.send_message("Order not found.", ephemeral=True)
            return
        new_status = select.values[0]
        orders[self.order_id]["status"] = new_status
        save_orders(orders)
        await interaction.response.send_message(f"✅ Status updated to **{new_status}** for #{self.order_id}", ephemeral=True)

    # --- Edit Notes Button ---
    @discord.ui.button(label="Edit Notes", style=discord.ButtonStyle.blurple, emoji="📝")
    async def edit_notes(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditNotesModal(self.order_id)
        await interaction.response.send_modal(modal)

    # --- Edit Budget/Deadline Button ---
    @discord.ui.button(label="Edit Budget/Deadline", style=discord.ButtonStyle.gray, emoji="💰")
    async def edit_budget(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditBudgetModal(self.order_id)
        await interaction.response.send_modal(modal)

    # --- View Full Order ---
    @discord.ui.button(label="View Full Info", style=discord.ButtonStyle.green, emoji="📄")
    async def view_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        orders = load_orders()
        order = orders.get(self.order_id)
        embed = discord.Embed(
            title=f"📋 Full Order #{self.order_id}",
            color=discord.Color.purple()
        )
        for k, v in order.items():
            embed.add_field(name=k.capitalize(), value=str(v), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Create Invoice ---
    @discord.ui.button(label="Create Invoice", style=discord.ButtonStyle.red, emoji="🧾")
    async def create_invoice(self, interaction: discord.Interaction, button: discord.ui.Button):
        orders = load_orders()
        order = orders.get(self.order_id)
        if not order:
            await interaction.response.send_message("❌ Order not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🧾 Invoice for Order #{self.order_id}",
            color=discord.Color.purple()
        )
        embed.add_field(name="Client", value=f"<@{order['client']}>", inline=True)
        embed.add_field(name="Budget", value=order['budget'], inline=True)
        embed.add_field(name="Deadline", value=order['deadline'], inline=True)
        embed.add_field(name="Status", value=order['status'], inline=True)
        embed.add_field(name="Notes", value=order['notes'], inline=False)
        embed.set_footer(text=f"Generated by {interaction.user}")

        await interaction.response.send_message(embed=embed)

# ===================================================
# MODALS
# ===================================================
class EditNotesModal(discord.ui.Modal, title="Edit Order Notes"):
    def __init__(self, order_id):
        super().__init__()
        self.order_id = order_id
        self.notes_input = discord.ui.TextInput(
            label="New Notes",
            style=discord.TextStyle.paragraph,
            placeholder="Enter updated notes here...",
            required=True
        )
        self.add_item(self.notes_input)

    async def on_submit(self, interaction: discord.Interaction):
        orders = load_orders()
        if self.order_id not in orders:
            await interaction.response.send_message("Order not found.", ephemeral=True)
            return

        orders[self.order_id]["notes"] = self.notes_input.value
        save_orders(orders)
        await interaction.response.send_message(f"✅ Notes updated for Order #{self.order_id}", ephemeral=True)

class EditBudgetModal(discord.ui.Modal, title="Edit Budget / Deadline"):
    def __init__(self, order_id):
        super().__init__()
        self.order_id = order_id
        self.budget_input = discord.ui.TextInput(
            label="New Budget",
            style=discord.TextStyle.short,
            placeholder="Enter new budget",
            required=False
        )
        self.deadline_input = discord.ui.TextInput(
            label="New Deadline",
            style=discord.TextStyle.short,
            placeholder="Enter new deadline",
            required=False
        )
        self.add_item(self.budget_input)
        self.add_item(self.deadline_input)

    async def on_submit(self, interaction: discord.Interaction):
        orders = load_orders()
        if self.order_id not in orders:
            await interaction.response.send_message("Order not found.", ephemeral=True)
            return

        if self.budget_input.value:
            orders[self.order_id]["budget"] = self.budget_input.value
        if self.deadline_input.value:
            orders[self.order_id]["deadline"] = self.deadline_input.value
        save_orders(orders)
        await interaction.response.send_message(f"✅ Budget/Deadline updated for Order #{self.order_id}", ephemeral=True)

# ===================================================
async def setup(bot):
    await bot.add_cog(Orders(bot))
