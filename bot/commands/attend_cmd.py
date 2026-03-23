"""Attendance command handlers."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..game_utils import (
    KEY_ATTEND_STREAK,
    KEY_LAST_ATTEND,
    SHEET_ATTENDANCE,
    add_gold,
    ensure_attendance,
    ensure_stats,
    ensure_user,
    get_actor_identity,
    get_gold,
    mark_dirty,
    to_int,
)


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def cmd_attend(user_id: str, nickname: str, data: dict[str, Any]) -> str:
    user = ensure_user(data, user_id, nickname)
    ensure_stats(data, user_id, nickname)
    record = ensure_attendance(data, user_id, nickname)

    today = date.today()
    last_attend = _parse_date(str(record.get(KEY_LAST_ATTEND, "")))
    if last_attend == today:
        streak = to_int(record.get(KEY_ATTEND_STREAK, 0))
        return f"\uc624\ub298\uc740 \uc774\ubbf8 \ucd9c\uc11d\ud588\uc2b5\ub2c8\ub2e4. \ud604\uc7ac \uc5f0\uc18d \ucd9c\uc11d {streak}\uc77c, \uc794\uc561 {get_gold(user)} \uace8\ub4dc\uc785\ub2c8\ub2e4."

    streak = 1
    if last_attend == today - timedelta(days=1):
        streak = to_int(record.get(KEY_ATTEND_STREAK, 0)) + 1

    reward = to_int(data.get("config", {}).get("\ucd9c\uc11d\ubcf4\uc0c1"), 100)
    balance = add_gold(data, user, reward)

    record[KEY_LAST_ATTEND] = today.isoformat()
    record[KEY_ATTEND_STREAK] = streak
    mark_dirty(data, SHEET_ATTENDANCE)
    return f"\ucd9c\uc11d \uc644\ub8cc. {reward} \uace8\ub4dc\ub97c \ubc1b\uc558\uc2b5\ub2c8\ub2e4. \uc5f0\uc18d \ucd9c\uc11d {streak}\uc77c, \ud604\uc7ac \uc794\uc561 {balance} \uace8\ub4dc\uc785\ub2c8\ub2e4."


async def handle(parsed: dict[str, Any], comment: dict[str, Any], data: dict[str, Any]) -> str:
    _ = parsed
    user_id, nickname = get_actor_identity(comment)
    if not user_id:
        return "\ucd9c\uc11d \ucc98\ub9ac\uc5d0 \ud544\uc694\ud55c \uc0ac\uc6a9\uc790 \uc815\ubcf4\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4."
    return cmd_attend(user_id, nickname, data)
