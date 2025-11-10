import discord
from discord import app_commands
from typing import Callable

import config

# Custom permission failure so we can send friendly errors
class PermissionDenied(app_commands.CheckFailure):
    pass


def _has_named_role(member: discord.Member, role_name: str) -> bool:
    """Check if a member has a role by name (case-sensitive)."""
    return discord.utils.get(member.roles, name=role_name) is not None


def in_allowed_guilds() -> Callable:
    """Allow only in configured guilds."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild_id not in config.GUILD_IDS:
            raise PermissionDenied(
                "This bot only functions inside **Hububba’s Coding World** and **Project Infinite ∞**."
            )
        return True
    return app_commands.check(predicate)


def perm_level(level: str) -> Callable:
    """
    level: 'staff' | 'admin' | 'any'
    - 'any': no role gate but still requires being in an allowed guild.
    - SUPER_ROLE_NAME always grants access.
    """
    valid = {"staff", "admin", "any"}
    if level not in valid:
        raise ValueError(f"Invalid perm level: {level}")

    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDenied("Members only.")

        member: discord.Member = interaction.user  # type: ignore

        # 1. Must be in allowed guild
        if interaction.guild is None or interaction.guild_id not in config.GUILD_IDS:
            raise PermissionDenied(
                "This bot only functions inside **Hububba’s Coding World** and **Project Infinite ∞**."
            )

        # 2. Owner or super role bypasses all checks
        if member.guild.owner_id == member.id or _has_named_role(member, config.SUPER_ROLE_NAME):
            return True

        # 3. Admin perms or role always pass
        if member.guild_permissions.administrator or _has_named_role(member, config.ADMIN_ROLE_NAME):
            return True

        # 4. Handle specific levels
        if level == "any":
            return True

        if level == "staff":
            if _has_named_role(member, config.STAFF_ROLE_NAME):
                return True
            raise PermissionDenied("You need the **Staff Perms Role** (or higher) for this command.")

        # Should never hit here
        raise PermissionDenied("Permission denied.")
    return app_commands.check(predicate)
