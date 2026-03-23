"""Gacha command handlers."""

from __future__ import annotations

import random
from typing import Any

from ..game_utils import (
    add_gold,
    ensure_stats,
    ensure_user,
    get_actor_identity,
    get_gold,
    stable_index,
    today_local,
    to_int,
)

CMD_FORTUNE = "\uc6b4\uc138"
CMD_DRAW = "\ubf51\uae30"
CMD_GAMBLE = "\ub3c4\ubc15"


def cmd_fortune(user_id: str, data: dict[str, Any]) -> str:
    random_list = data.get("random_list", [])
    if not random_list:
        return "\ub79c\ub364 \ubaa9\ub85d\uc774 \ube44\uc5b4 \uc788\uc2b5\ub2c8\ub2e4."

    seed = f"{user_id}:{today_local()}"
    index = stable_index(seed, len(random_list))
    return f"\uc624\ub298\uc758 \uc6b4\uc138: {random_list[index]}"


def cmd_draw(data: dict[str, Any]) -> str:
    random_list = data.get("random_list", [])
    if not random_list:
        return "\ub79c\ub364 \ubaa9\ub85d\uc774 \ube44\uc5b4 \uc788\uc2b5\ub2c8\ub2e4."
    return f"\ubf51\uae30 \uacb0\uacfc: {random.choice(random_list)}"


def cmd_gamble(user_id: str, nickname: str, amount_text: str, data: dict[str, Any]) -> str:
    amount = to_int(amount_text, 0)
    if amount <= 0:
        return "\ub3c4\ubc15 \uae08\uc561\uc740 1 \uc774\uc0c1\uc774\uc5b4\uc57c \ud569\ub2c8\ub2e4."

    user = ensure_user(data, user_id, nickname)
    ensure_stats(data, user_id, nickname)
    balance = get_gold(user)
    if balance < amount:
        return f"\uc794\uc561\uc774 \ubd80\uc871\ud569\ub2c8\ub2e4. \ud604\uc7ac {balance} \uace8\ub4dc\uc785\ub2c8\ub2e4."

    if random.random() < 0.5:
        new_balance = add_gold(data, user, amount)
        return f"\ub3c4\ubc15 \uc131\uacf5. {amount} \uace8\ub4dc\ub97c \ucd94\uac00\ub85c \uc5bb\uc5c8\uc2b5\ub2c8\ub2e4. \ud604\uc7ac \uc794\uc561 {new_balance} \uace8\ub4dc\uc785\ub2c8\ub2e4."

    new_balance = add_gold(data, user, -amount)
    return f"\ub3c4\ubc15 \uc2e4\ud328. {amount} \uace8\ub4dc\ub97c \uc783\uc5c8\uc2b5\ub2c8\ub2e4. \ud604\uc7ac \uc794\uc561 {new_balance} \uace8\ub4dc\uc785\ub2c8\ub2e4."


async def handle(parsed: dict[str, Any], comment: dict[str, Any], data: dict[str, Any]) -> str:
    command_name = parsed["cmd"]
    args = parsed.get("args", [])
    user_id, nickname = get_actor_identity(comment)

    if command_name == CMD_FORTUNE:
        if not user_id:
            return "\uc6b4\uc138 \ud655\uc778\uc5d0 \ud544\uc694\ud55c \uc0ac\uc6a9\uc790 \uc815\ubcf4\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4."
        return cmd_fortune(user_id, data)

    if command_name == CMD_DRAW:
        return cmd_draw(data)

    if command_name == CMD_GAMBLE:
        if not user_id:
            return "\ub3c4\ubc15 \ucc98\ub9ac\uc5d0 \ud544\uc694\ud55c \uc0ac\uc6a9\uc790 \uc815\ubcf4\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4."
        if not args:
            return "\ub3c4\ubc15 \uae08\uc561\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694. \uc608: [\ub3c4\ubc15/100]"
        return cmd_gamble(user_id, nickname, args[0], data)

    return "\uc9c0\uc6d0\ud558\uc9c0 \uc54a\ub294 \ub79c\ub364 \uba85\ub839\uc5b4\uc785\ub2c8\ub2e4."
