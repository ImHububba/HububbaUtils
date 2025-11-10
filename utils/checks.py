# utils/checks.py
import discord
from discord import app_commands
from typing import Callable
import config

# Custom permission failure so we can send friendly errors
class PermissionDenied(app_commands.CheckFailure):
    pass


# --- Role helper ---
def _has_named_role(member: discord.Member, role_name: str) -> bool:
    return discord.utils.get(member.roles, name=role_name) is not None


# --- Guild restriction check (used by older cogs) ---
def in_home_guild() -> Callable:
    """Restrict commands to Hububba's Coding World or Project Infinite."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild_id not in [
            config.HUBUBBA_GUILD_ID,
            config.PROJECT_INFINITE_ID
        ]:
            raise PermissionDenied("This bot only functions inside **Hububba's Coding World** or **Project Infinite ∞**.")
        return True
    return app_commands.check(predicate)


# --- Newer generic allowed guild check (kept for future use) ---
def in_allowed_guilds() -> Callable:
    """Restrict to allowed guilds list in config."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild_id not in [
            config.HUBUBBA_GUILD_ID,
            config.PROJECT_INFINITE_ID
        ]:
            raise PermissionDenied("This bot only functions inside authorized guilds.")
        return True
    return app_commands.check(predicate)


# --- Permission levels ---
def perm_level(level: str) -> Callable:
    """
    level: 'staff' | 'admin' | 'any' (any = no role gate but still respects in_home_guild)
    SUPER_ROLE_NAME always grants access.
    """
    valid = {"staff", "admin", "any"}
    if level not in valid:
        raise ValueError(f"Invalid perm level: {level}")

    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDenied("Members only.")

        member: discord.Member = interaction.user  # type: ignore

        # Always allow the server owner and those with the super role
        if member.guild.owner_id == member.id:
            return True
        if _has_named_role(member, config.SUPER_ROLE_NAME):
            return True

        # Admins also pass administrator perm
        if member.guild_permissions.administrator:
            return True

        if level == "any":
            return True

        if level == "admin":
            if _has_named_role(member, config.ADMIN_ROLE_NAME):
                return True
            raise PermissionDenied("You need the **Admin+ Perms** role for this command.")

        if level == "staff":
            if _has_named_role(member, config.STAFF_ROLE_NAME) or _has_named_role(member, config.ADMIN_ROLE_NAME):
                return True
            raise PermissionDenied("You need the **Staff Perms Role** (or higher) for this command.")

        raise PermissionDenied("Permission denied.")
    return app_commands.check(predicate)
