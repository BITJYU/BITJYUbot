"""Shared state helpers for non-battle game features."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

SHEET_MEMBERS = "\ubaa9\ub85d"
SHEET_INVENTORY = "\uc778\ubca4\ud1a0\ub9ac"
SHEET_PURCHASE_LOG = "\uad6c\ub9e4\ub0b4\uc5ed"
SHEET_ATTENDANCE = "\ucd9c\uc11d"

KEY_NICKNAME = "\ub2c9\ub124\uc784"
KEY_GOLD = "\uace8\ub4dc"
KEY_UPDATED_AT = "\ub9c8\uc9c0\ub9c9\uc5c5\ub370\uc774\ud2b8"
KEY_ITEM_NAME = "\uc544\uc774\ud15c\uba85"
KEY_QUANTITY = "\uc218\ub7c9"
KEY_DURABILITY = "\ub0b4\uad6c\ub3c4"
KEY_LAST_ATTEND = "\ub9c8\uc9c0\ub9c9\ucd9c\uc11d\uc77c"
KEY_ATTEND_STREAK = "\uc5f0\uc18d\ucd9c\uc11d\uc77c\uc218"
KEY_PRICE = "\uac00\uaca9"
KEY_PURCHASED_AT = "\uad6c\ub9e4\uc2dc\uac01"

DEFAULT_STATS = {
    "HP": 100,
    "ATK": 10,
    "DEF": 5,
    "SPD": 5,
    "MP": 50,
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def today_local() -> str:
    return datetime.now().date().isoformat()


def mark_dirty(data: dict[str, Any], *sheet_names: str) -> None:
    dirty = data.setdefault("_dirty", set())
    dirty.update(sheet_names)


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def normalize_name(value: str) -> str:
    return (value or "").replace(" ", "").strip().lower()


def ensure_user(data: dict[str, Any], user_id: str, nickname: str) -> dict[str, Any]:
    users = data.setdefault("users", {})
    user = users.get(user_id)
    if user is None:
        user = {
            "user_id": user_id,
            KEY_NICKNAME: nickname or user_id,
            KEY_GOLD: 0,
            KEY_UPDATED_AT: now_iso(),
            **DEFAULT_STATS,
        }
        users[user_id] = user
        mark_dirty(data, SHEET_MEMBERS, SHEET_INVENTORY)
    else:
        changed = False
        if nickname and user.get(KEY_NICKNAME) != nickname:
            user[KEY_NICKNAME] = nickname
            changed = True
        if KEY_GOLD not in user:
            user[KEY_GOLD] = 0
            changed = True
        if KEY_UPDATED_AT not in user:
            user[KEY_UPDATED_AT] = ""
            changed = True
        for stat_name, default in DEFAULT_STATS.items():
            if stat_name not in user or user.get(stat_name) in ("", None):
                user[stat_name] = default
                changed = True
        if changed:
            mark_dirty(data, SHEET_MEMBERS, SHEET_INVENTORY)

    data["stats"] = data.get("users", {})
    return user


def ensure_stats(data: dict[str, Any], user_id: str, nickname: str) -> dict[str, Any]:
    return ensure_user(data, user_id, nickname)


def ensure_inventory(data: dict[str, Any], user_id: str) -> list[dict[str, Any]]:
    inventory = data.setdefault("inventory", {})
    if user_id not in inventory:
        inventory[user_id] = []
    return inventory[user_id]


def ensure_attendance(data: dict[str, Any], user_id: str, nickname: str) -> dict[str, Any]:
    attendance = data.setdefault("attendance", {})
    record = attendance.get(user_id)
    if record is None:
        record = {
            "user_id": user_id,
            KEY_NICKNAME: nickname or user_id,
            KEY_LAST_ATTEND: "",
            KEY_ATTEND_STREAK: 0,
        }
        attendance[user_id] = record
        mark_dirty(data, SHEET_ATTENDANCE)
    else:
        if nickname and record.get(KEY_NICKNAME) != nickname:
            record[KEY_NICKNAME] = nickname
            mark_dirty(data, SHEET_ATTENDANCE)
    return record


def get_gold(user: dict[str, Any]) -> int:
    return to_int(user.get(KEY_GOLD, 0))


def set_gold(data: dict[str, Any], user: dict[str, Any], amount: int) -> None:
    user[KEY_GOLD] = amount
    user[KEY_UPDATED_AT] = now_iso()
    mark_dirty(data, SHEET_INVENTORY)


def add_gold(data: dict[str, Any], user: dict[str, Any], amount: int) -> int:
    new_amount = get_gold(user) + amount
    set_gold(data, user, new_amount)
    return new_amount


def find_item(shop_data: list[dict[str, Any]], item_name: str) -> dict[str, Any] | None:
    normalized = normalize_name(item_name)
    if not normalized:
        return None
    for item in shop_data:
        candidates = [
            item.get(KEY_ITEM_NAME, ""),
            item.get("name", ""),
        ]
        if any(normalized in normalize_name(candidate) for candidate in candidates):
            return item
    return None


def get_shop_item_name(item: dict[str, Any]) -> str:
    return str(item.get(KEY_ITEM_NAME, "") or item.get("name", "") or "")


def get_inventory_item(items: list[dict[str, Any]], item_name: str) -> dict[str, Any] | None:
    normalized = normalize_name(item_name)
    for item in items:
        if normalized == normalize_name(str(item.get(KEY_ITEM_NAME, ""))):
            return item
    return None


def upsert_inventory_item(
    data: dict[str, Any],
    user_id: str,
    nickname: str,
    item_name: str,
    quantity: int,
    durability: int = 0,
) -> dict[str, Any]:
    items = ensure_inventory(data, user_id)
    existing = get_inventory_item(items, item_name)
    if existing is None:
        existing = {
            "user_id": user_id,
            KEY_NICKNAME: nickname or user_id,
            KEY_ITEM_NAME: item_name,
            KEY_QUANTITY: quantity,
            KEY_DURABILITY: durability,
        }
        items.append(existing)
    else:
        existing[KEY_NICKNAME] = nickname or existing.get(KEY_NICKNAME, user_id)
        existing[KEY_QUANTITY] = to_int(existing.get(KEY_QUANTITY, 0)) + quantity
        if durability:
            existing[KEY_DURABILITY] = durability
    mark_dirty(data, SHEET_INVENTORY)
    return existing


def add_purchase_log(
    data: dict[str, Any],
    user_id: str,
    nickname: str,
    item_name: str,
    quantity: int,
    price: int,
) -> None:
    logs = data.setdefault("purchase_log", [])
    logs.append(
        {
            "user_id": user_id,
            KEY_NICKNAME: nickname or user_id,
            KEY_ITEM_NAME: item_name,
            KEY_QUANTITY: quantity,
            KEY_PRICE: price,
            KEY_PURCHASED_AT: now_iso(),
        }
    )
    mark_dirty(data, SHEET_PURCHASE_LOG)


def stable_index(seed: str, size: int) -> int:
    if size <= 0:
        return 0
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest, 16) % size


def get_actor_identity(comment: dict[str, Any]) -> tuple[str, str]:
    user_id = str(comment.get("author_id", "") or "")
    nickname = str(comment.get("nickname", "") or user_id)
    return user_id, nickname
