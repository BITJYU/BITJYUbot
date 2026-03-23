"""Command parsing and routing helpers."""

from __future__ import annotations

import re
from typing import Any

from .commands import admin_cmd, attend_cmd, battle_cmd, economy_cmd, gacha_cmd, random_cmd

COMMAND_PATTERN = re.compile(r"\[([^\]]+)\]")

RANDOM_COMMANDS = {
    "\uc8fc\uc0ac\uc704",
    "YN",
    "\uc120\ud0dd",
    "\ub3d9\uc804",
}
ECONOMY_COMMANDS = {
    "\uc794\uc561",
    "\uc0c1\uc810",
    "\uad6c\ub9e4",
    "\uc0ac\uc6a9",
    "\uc591\ub3c4",
    "\uc778\ubca4\ud1a0\ub9ac",
}
GACHA_COMMANDS = {
    "\uc6b4\uc138",
    "\ubf51\uae30",
    "\ub3c4\ubc15",
}
ATTEND_COMMANDS = {
    "\ucd9c\uc11d",
}
BATTLE_COMMANDS = {
    "\uacf5\uaca9",
    "\uc2a4\ud0ac",
    "\ubc29\uc5b4",
    "\ud68c\ubcf5",
    "\uc804\ud22c\uc0c1\ud0dc",
}
ADMIN_COMMANDS = {
    "\uacb0\ud22c\uc2e0\uccad",
    "\uc9c0\uae09",
    "\ucc28\uac10",
}


def parse_command(text: str) -> dict[str, Any] | None:
    """Parse the first [command/arg1/arg2] block from text."""
    match = COMMAND_PATTERN.search(text or "")
    if not match:
        return None

    parts = [part.strip() for part in match.group(1).split("/")]
    if not parts or not parts[0]:
        return None

    return {
        "raw": match.group(0),
        "cmd": parts[0],
        "args": parts[1:],
    }


def is_battle_command(command_name: str) -> bool:
    return command_name in BATTLE_COMMANDS


def find_battle_by_post_key(data: dict[str, Any], post_key: str) -> dict[str, Any] | None:
    if not post_key:
        return None

    for battle in data.get("battles", {}).values():
        if battle.get("status") != "\uc9c4\ud589\uc911":
            continue
        if battle.get("post_key") == post_key:
            return battle
    return None


async def dispatch_command(
    parsed: dict[str, Any],
    comment: dict[str, Any],
    data: dict[str, Any],
    post_key: str | None = None,
) -> str | None:
    """Route a parsed command to the appropriate command module."""
    command_name = parsed["cmd"]

    if command_name in RANDOM_COMMANDS:
        return await random_cmd.handle(parsed, comment, data)

    if command_name in ECONOMY_COMMANDS:
        return await economy_cmd.handle(parsed, comment, data)

    if command_name in GACHA_COMMANDS:
        return await gacha_cmd.handle(parsed, comment, data)

    if command_name in ATTEND_COMMANDS:
        return await attend_cmd.handle(parsed, comment, data)

    if command_name in ADMIN_COMMANDS:
        return await admin_cmd.handle(parsed, comment, data, post_key=post_key)

    if command_name in BATTLE_COMMANDS:
        battle = find_battle_by_post_key(data, post_key or "")
        if not battle:
            return None
        return await battle_cmd.handle(parsed, comment, battle, data)

    return "\uc9c0\uc6d0\ud558\uc9c0 \uc54a\ub294 \uba85\ub839\uc5b4\uc785\ub2c8\ub2e4."
