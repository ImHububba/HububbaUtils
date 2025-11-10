# cogs/orders.py
import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
import discord
from discord import app_commands
from discord.ext import commands

DATA_DIR = "data"
ORDERS_PATH = os.path.join(DATA_DIR, "orders.json")

def _ensure_store():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ORDERS_PATH):
        with open(ORDERS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)

def _safe_load() -> List[dict]:
    _ensure_store()
    try:
        with open(ORDERS_PATH, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if not raw:
                return []
            return json.loads(raw)
    except Exception:
        return []

def _safe_save(items: List[dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = ORDERS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    os.replace(tmp, ORDERS_PATH)

def _next_order_id(items: List[dict]) -> int:
    if not items:
        return 1
    return max(int(x.get("id", 0)) for x in items) + 1

@dataclass
class Order:
    id: int
    user_id: int
    ticket_channel_id: Optional[int]
    title: str
    status: str  # e.g. "open", "in_progress", "completed", "cancelled"
    budget: Optional[str] = None
    deadline: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self):
        return asdict(self)

def create_order_from_ticket(
    user_id: int,
    ticket_channel_id: int,
    title: str,
    budget: Optional[str],
    deadline: Optional[str],
    notes: Optional[str],
) -> Order:
    items = _safe_load()
    oid = _next_order_id(items)
    order = Order(
        id=oid,
        user_id=user_id,
        ticket_channel_id=ticket_channel_id,
        title=title or f"Commission #{oid}",
        status="open",
        budget=budget,
        deadline=deadline,
        notes=notes,
    )
    items.append(order.to_dict())
    _safe_save(items)
    return order

def list_orders() -> List[Order]:
    return [Order(**o) for o in _safe_load()]

def get_order(oid: int) -> Optional[Order]:
    for o in _safe_load():
        if int(o.get("id", 0)) == oid:
            return Order(**o)
    return None

def save_order(order: Order):
    items = _safe_load()
    for i, o in enumerate(items):
        if int(o.get("id", 0)) == order.id:
            items[i] = order.to_dict()
            break
    else:
        items.append(order.to_dict())
    _safe_save(items)

class OrdersCog(commands.Cog, name="Orders"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /order list
    @app_commands.command(name="order_list", description="List all orders.")
    @app_commands.guild_only()
    async def order_list(self, interaction: discord.Interaction):
        items = list_orders()
        if not items:
            await interaction.response.send_message("No orders yet.", ephemeral=True)
            return
        chunks = []
        for o in items:
            line = f"**#{o.id}** — **{discord.utils.escape_markdown(o.title)}** · {o.status}"
            if o.ticket_channel_id:
                line += f" · <#{o.ticket_channel_id}>"
            chunks.append(line)
        msg = "\n".join(chunks)
        await interaction.response.send_message(msg, ephemeral=True)

    # /order manage
    @app_commands.command(name="order_manage", description="Edit an existing order.")
    @app_commands.describe(
        id="Order ID number",
        title="New title",
        status="open / in_progress / completed / cancelled",
        budget="Update budget",
        deadline="Update deadline",
        notes="Update notes"
    )
    @app_commands.guild_only()
    async def order_manage(
        self,
        interaction: discord.Interaction,
        id: int,
        title: Optional[str] = None,
        status: Optional[str] = None,
        budget: Optional[str] = None,
        deadline: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        o = get_order(id)
        if not o:
            await interaction.response.send_message(f"Order #{id} not found.", ephemeral=True)
            return
        if title is not None: o.title = title
        if status is not None: o.status = status
        if budget is not None: o.budget = budget
        if deadline is not None: o.deadline = deadline
        if notes is not None: o.notes = notes
        save_order(o)
        await interaction.response.send_message(f"Updated order **#{o.id}**.", ephemeral=True)

async def setup(bot: commands.Bot):
    cog = OrdersCog(bot)
    await bot.add_cog(cog)
    # optional debug logging
    if hasattr(bot, "logger"):
        bot.logger.info("✅ Registered 4 commands from Orders")
