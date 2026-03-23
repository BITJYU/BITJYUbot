"""Random command handlers."""

from __future__ import annotations

import random
import re
from typing import Any

DICE_PATTERN = re.compile(r"^\s*(\d+)[dD](\d+)(?:([+-])(\d+))?\s*$")

MSG_DICE_INVALID = "\uc8fc\uc0ac\uc704 \ud615\uc2dd\uc774 \uc62c\ubc14\ub974\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. \uc608: [\uc8fc\uc0ac\uc704/2d6+3]"
MSG_DICE_RANGE = "\uc8fc\uc0ac\uc704 \ubc94\uc704\uac00 \uc62c\ubc14\ub974\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4."
MSG_DICE_PROMPT = "\uc8fc\uc0ac\uc704 \uc2dd\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694. \uc608: [\uc8fc\uc0ac\uc704/2d6+3]"
MSG_CHOICE_PROMPT = "\uc120\ud0dd\uc9c0\ub294 2\uac1c \uc774\uc0c1 \uc785\ub825\ud574\uc8fc\uc138\uc694. \uc608: [\uc120\ud0dd/\uc9dc\uc7a5\uba74/\ud53c\uc790/\uce58\ud0a8]"
MSG_UNSUPPORTED = "\uc9c0\uc6d0\ud558\uc9c0 \uc54a\ub294 \ub79c\ub364 \uba85\ub839\uc5b4\uc785\ub2c8\ub2e4."
CMD_DICE = "\uc8fc\uc0ac\uc704"
CMD_CHOICE = "\uc120\ud0dd"
CMD_COIN = "\ub3d9\uc804"
WORD_YES = "\uc608"
WORD_NO = "\uc544\ub2c8\uc624"
WORD_HEADS = "\uc55e\uba74"
WORD_TAILS = "\ub4b7\uba74"


def roll_dice(expression: str) -> str:
    match = DICE_PATTERN.match(expression or "")
    if not match:
        return MSG_DICE_INVALID

    count = int(match.group(1))
    sides = int(match.group(2))
    op = match.group(3)
    modifier = int(match.group(4) or 0)

    if count <= 0 or sides <= 0 or count > 100:
        return MSG_DICE_RANGE

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    modifier_text = ""

    if op == "+":
        total += modifier
        modifier_text = f" +{modifier}"
    elif op == "-":
        total -= modifier
        modifier_text = f" -{modifier}"

    joined = ", ".join(str(value) for value in rolls)
    return f"{expression} \uacb0\uacfc: [ {joined} ]{modifier_text} \ud569\uacc4 {total}"


def roll_yn() -> str:
    return random.choice([WORD_YES, WORD_NO])


def roll_choice(options: list[str]) -> str:
    cleaned = [option.strip() for option in options if option.strip()]
    if len(cleaned) < 2:
        return MSG_CHOICE_PROMPT
    return f"\uc120\ud0dd \uacb0\uacfc: {random.choice(cleaned)}"


def roll_coin() -> str:
    return random.choice([WORD_HEADS, WORD_TAILS])


async def handle(parsed: dict[str, Any], comment: dict[str, Any], data: dict[str, Any]) -> str:
    _ = (comment, data)
    command_name = parsed["cmd"]
    args = parsed.get("args", [])

    if command_name == CMD_DICE:
        if not args:
            return MSG_DICE_PROMPT
        return roll_dice(args[0])

    if command_name == "YN":
        return roll_yn()

    if command_name == CMD_CHOICE:
        return roll_choice(args)

    if command_name == CMD_COIN:
        return roll_coin()

    return MSG_UNSUPPORTED
