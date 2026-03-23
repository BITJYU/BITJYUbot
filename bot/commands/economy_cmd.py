"""Economy command handlers."""

from __future__ import annotations

from typing import Any

from ..game_utils import (
    KEY_DURABILITY,
    KEY_GOLD,
    KEY_ITEM_NAME,
    KEY_NICKNAME,
    KEY_PRICE,
    KEY_QUANTITY,
    add_purchase_log,
    ensure_inventory,
    ensure_stats,
    ensure_user,
    find_item,
    get_actor_identity,
    get_gold,
    get_shop_item_name,
    mark_dirty,
    set_gold,
    to_int,
    upsert_inventory_item,
)

SHEET_SHOP = "\uc0c1\uc810"
CMD_BALANCE = "\uc794\uc561"
CMD_SHOP = "\uc0c1\uc810"
CMD_BUY = "\uad6c\ub9e4"
CMD_USE = "\uc0ac\uc6a9"
CMD_TRANSFER = "\uc591\ub3c4"
CMD_INVENTORY = "\uc778\ubca4\ud1a0\ub9ac"


def cmd_balance(user_id: str, nickname: str, data: dict[str, Any]) -> str:
    user = ensure_user(data, user_id, nickname)
    ensure_stats(data, user_id, nickname)
    balance = get_gold(user)
    return f"{user.get(KEY_NICKNAME, nickname)}\ub2d8\uc758 \ud604\uc7ac \uc794\uc561\uc740 {balance} \uace8\ub4dc\uc785\ub2c8\ub2e4."


def cmd_shop(data: dict[str, Any]) -> str:
    shop_items = data.get("shop", [])
    if not shop_items:
        return "\uc0c1\uc810 \ubaa9\ub85d\uc774 \ube44\uc5b4 \uc788\uc2b5\ub2c8\ub2e4."

    lines = ["\uc0c1\uc810 \ubaa9\ub85d"]
    for item in shop_items[:20]:
        name = get_shop_item_name(item) or "\uc774\ub984\uc5c6\uc74c"
        price = to_int(item.get(KEY_PRICE, item.get("price", 0)))
        stock_raw = item.get("\uc7ac\uace0", "")
        stock = "\ubb34\uc81c\ud55c" if str(stock_raw).strip() == "" else str(stock_raw)
        image_url = str(item.get("\uc774\ubbf8\uc9c0URL", "") or "")
        line = f"- {name} / {price}\uace8\ub4dc / \uc7ac\uace0 {stock}"
        if image_url:
            line += f" / {image_url}"
        lines.append(line)
    return "\n".join(lines)


def cmd_inventory(user_id: str, nickname: str, data: dict[str, Any]) -> str:
    user = ensure_user(data, user_id, nickname)
    ensure_stats(data, user_id, nickname)
    items = ensure_inventory(data, user_id)

    lines = [f"{nickname}\ub2d8\uc758 \uc778\ubca4\ud1a0\ub9ac", f"\uace8\ub4dc: {get_gold(user)}"]
    if not items:
        lines.append("- \ubcf4\uc720 \uc544\uc774\ud15c \uc5c6\uc74c")
        return "\n".join(lines)

    for item in items:
        name = str(item.get(KEY_ITEM_NAME, "") or "\uc774\ub984\uc5c6\uc74c")
        qty = to_int(item.get(KEY_QUANTITY, 0))
        durability = item.get(KEY_DURABILITY, "")
        extra = ""
        if str(durability).strip() not in ("", "0"):
            extra = f" / \ub0b4\uad6c\ub3c4 {durability}"
        lines.append(f"- {name} x{qty}{extra}")
    return "\n".join(lines)


def cmd_buy(user_id: str, nickname: str, item_name: str, qty_text: str, data: dict[str, Any]) -> str:
    user = ensure_user(data, user_id, nickname)
    ensure_stats(data, user_id, nickname)

    quantity = to_int(qty_text, 0)
    if quantity <= 0:
        return "\uad6c\ub9e4 \uc218\ub7c9\uc740 1 \uc774\uc0c1\uc774\uc5b4\uc57c \ud569\ub2c8\ub2e4."

    shop_item = find_item(data.get("shop", []), item_name)
    if not shop_item:
        return "\ud574\ub2f9 \uc544\uc774\ud15c\uc744 \uc0c1\uc810\uc5d0\uc11c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4."

    item_label = get_shop_item_name(shop_item)
    unit_price = to_int(shop_item.get(KEY_PRICE, shop_item.get("price", 0)))
    if unit_price < 0:
        return "\uc544\uc774\ud15c \uac00\uaca9 \uc124\uc815\uc774 \uc62c\ubc14\ub974\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4."

    stock_value = str(shop_item.get("\uc7ac\uace0", "")).strip()
    stock = None if stock_value == "" else to_int(stock_value, 0)
    if stock is not None and stock < quantity:
        return "\uc7ac\uace0\uac00 \ubd80\uc871\ud558\uc5ec \uad6c\ub9e4\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4."

    total_price = unit_price * quantity
    balance = get_gold(user)
    if balance < total_price:
        return f"\uc794\uc561\uc774 \ubd80\uc871\ud569\ub2c8\ub2e4. \ud544\uc694 {total_price} \uace8\ub4dc, \ud604\uc7ac {balance} \uace8\ub4dc\uc785\ub2c8\ub2e4."

    if stock is not None:
        shop_item["\uc7ac\uace0"] = stock - quantity
        mark_dirty(data, SHEET_SHOP)

    set_gold(data, user, balance - total_price)
    durability = to_int(shop_item.get(KEY_DURABILITY, 0))
    upsert_inventory_item(data, user_id, nickname, item_label, quantity, durability=durability)
    add_purchase_log(data, user_id, nickname, item_label, quantity, total_price)

    image_url = str(shop_item.get("\uc774\ubbf8\uc9c0URL", "") or "")
    image_text = f"\n\uc774\ubbf8\uc9c0: {image_url}" if image_url else ""
    return (
        f"{item_label} {quantity}\uac1c\ub97c \uad6c\ub9e4\ud588\uc2b5\ub2c8\ub2e4. \ucd1d {total_price} \uace8\ub4dc\uac00 \ucc28\uac10\ub418\uc5c8\uc2b5\ub2c8\ub2e4. "
        f"\ud604\uc7ac \uc794\uc561\uc740 {get_gold(user)} \uace8\ub4dc\uc785\ub2c8\ub2e4.{image_text}"
    )


async def handle(parsed: dict[str, Any], comment: dict[str, Any], data: dict[str, Any]) -> str:
    command_name = parsed["cmd"]
    args = parsed.get("args", [])
    user_id, nickname = get_actor_identity(comment)

    if not user_id and command_name != CMD_SHOP:
        return "\uc0ac\uc6a9\uc790 \uc815\ubcf4\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4."

    if command_name == CMD_BALANCE:
        return cmd_balance(user_id, nickname, data)

    if command_name == CMD_SHOP:
        return cmd_shop(data)

    if command_name == CMD_BUY:
        if len(args) < 2:
            return "\uad6c\ub9e4 \ud615\uc2dd\uc774 \uc62c\ubc14\ub974\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. \uc608: [\uad6c\ub9e4/\uacf5\uaca9\ub825\ud3ec\uc158/2]"
        return cmd_buy(user_id, nickname, args[0], args[1], data)

    if command_name == CMD_INVENTORY:
        return cmd_inventory(user_id, nickname, data)

    if command_name == CMD_USE:
        return "\uc0ac\uc6a9 \uae30\ub2a5\uc740 \ub2e4\uc74c \ub2e8\uacc4\uc5d0\uc11c \uad6c\ud604\ud560 \uc608\uc815\uc785\ub2c8\ub2e4."

    if command_name == CMD_TRANSFER:
        return "\uc591\ub3c4 \uae30\ub2a5\uc740 \ub2e4\uc74c \ub2e8\uacc4\uc5d0\uc11c \uad6c\ud604\ud560 \uc608\uc815\uc785\ub2c8\ub2e4."

    return "\uc9c0\uc6d0\ud558\uc9c0 \uc54a\ub294 \uacbd\uc81c \uba85\ub839\uc5b4\uc785\ub2c8\ub2e4."
