"""
permissions.py

Wspólna reguła "czy to administracja": albo rola ADMIN_ROLE_ID z config.py,
albo uprawnienie Discorda "Zarządzaj serwerem". Używane tam, gdzie
app_commands.checks.has_permissions nie wystarcza (np. w callbackach przycisków).
"""

import discord

import config


def is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.manage_guild:
        return True
    if config.ADMIN_ROLE_ID and any(role.id == config.ADMIN_ROLE_ID for role in member.roles):
        return True
    return False
