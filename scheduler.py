"""Daily scheduler for command posts and reserved posts."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import aiohttp

from bot.band_api import create_post
from bot.config import AppConfig
from bot.game_utils import mark_dirty
from bot.logging_utils import log_error, log_info
from bot.sheets import load_all_data, save_dirty_data
from bot.utils import parse_iso_datetime

SHEET_CONFIG = "\uc124\uc815"
SHEET_SCHEDULED_POSTS = "\uc870\uc0ac\ubaa9\ub85d"

CONFIG_COMMAND_POST_ENABLED = "COMMAND_POST_ENABLED"
CONFIG_COMMAND_POST_CONTENT = "COMMAND_POST_CONTENT"
CONFIG_CURRENT_COMMAND_POST_KEY = "CURRENT_COMMAND_POST_KEY"
CONFIG_CURRENT_COMMAND_POST_CREATED_AT = "CURRENT_COMMAND_POST_CREATED_AT"
CONFIG_TRACKED_BOT_POST_KEYS = "TRACKED_BOT_POST_KEYS"

DEFAULT_COMMAND_POST_CONTENT = (
    "\uc624\ub298\uc758 \uba85\ub839 \uac8c\uc2dc\uae00\uc785\ub2c8\ub2e4.\n"
    "\uc774 \uac8c\uc2dc\uae00 \ub313\uae00\uc5d0 [\uc794\uc561], [\uc0c1\uc810], [\ucd9c\uc11d], [\uc778\ubca4\ud1a0\ub9ac], [\uc6b4\uc138] \ud615\uc2dd\uc73c\ub85c \uc785\ub825\ud574\uc8fc\uc138\uc694."
)


async def main() -> None:
    config = AppConfig.from_env()
    data = load_all_data(config)

    try:
        async with aiohttp.ClientSession() as session:
            await run_scheduler(session, config, data)
    finally:
        save_dirty_data(data)


async def run_scheduler(
    session: aiohttp.ClientSession,
    config: AppConfig,
    data: dict[str, Any],
) -> None:
    await create_daily_command_post(session, config, data)
    await publish_reserved_posts(session, config, data)


async def create_daily_command_post(
    session: aiohttp.ClientSession,
    config: AppConfig,
    data: dict[str, Any],
) -> None:
    if not _config_enabled(data, CONFIG_COMMAND_POST_ENABLED, default=True):
        return
    if _already_created_today(data):
        return

    content = str(data.get("config", {}).get(CONFIG_COMMAND_POST_CONTENT, "") or DEFAULT_COMMAND_POST_CONTENT)
    created = await create_post(session, config, content)
    if not created:
        log_error("Failed to create daily command post.")
        return

    post_key = str(created.get("post_key", "") or "")
    if not post_key:
        log_error("Daily command post was created without a post_key in the response.")
        return

    data.setdefault("config", {})[CONFIG_CURRENT_COMMAND_POST_KEY] = post_key
    data["config"][CONFIG_CURRENT_COMMAND_POST_CREATED_AT] = datetime.now(UTC).isoformat()
    _track_bot_post_key(data, post_key)
    mark_dirty(data, SHEET_CONFIG)
    log_info(f"Daily command post created: {post_key[:8]}****")


async def publish_reserved_posts(
    session: aiohttp.ClientSession,
    config: AppConfig,
    data: dict[str, Any],
) -> None:
    now = datetime.now(UTC)
    updated = False

    for row in data.get("scheduled_posts", []):
        status = str(row.get("\ubc1c\uc1a1\uc5ec\ubd80", "") or "").strip()
        scheduled_at = parse_iso_datetime(str(row.get("\uc608\uc57d\uc2dc\uac01", "") or ""))
        content = str(row.get("\ub0b4\uc6a9", "") or "").strip()

        if status not in ("", "\ub300\uae30", "\ub300\uae30\uc911"):
            continue
        if not scheduled_at or scheduled_at > now:
            continue
        if not content:
            continue

        created = await create_post(session, config, content)
        if not created:
            log_error("Failed to publish a reserved post.")
            continue

        post_key = str(created.get("post_key", "") or "")
        if post_key:
            _track_bot_post_key(data, post_key)
        row["\ubc1c\uc1a1\uc5ec\ubd80"] = "\uc644\ub8cc"
        if "\ubc1c\uc1a1\uc2dc\uac01" in row:
            row["\ubc1c\uc1a1\uc2dc\uac01"] = now.isoformat()
        updated = True

    if updated:
        mark_dirty(data, SHEET_SCHEDULED_POSTS)
        log_info("Reserved posts published.")


def _config_enabled(data: dict[str, Any], key: str, default: bool) -> bool:
    raw = str(data.get("config", {}).get(key, "") or "").strip().lower()
    if raw == "":
        return default
    return raw not in {"0", "false", "off", "no"}


def _already_created_today(data: dict[str, Any]) -> bool:
    raw = str(data.get("config", {}).get(CONFIG_CURRENT_COMMAND_POST_CREATED_AT, "") or "").strip()
    if not raw:
        return False
    created_at = parse_iso_datetime(raw)
    if not created_at:
        return False
    return created_at.date() == datetime.now(UTC).date()


def _track_bot_post_key(data: dict[str, Any], post_key: str) -> None:
    tracked = _get_tracked_bot_post_keys(data)
    if post_key in tracked:
        return
    tracked = [post_key] + tracked
    data.setdefault("config", {})[CONFIG_TRACKED_BOT_POST_KEYS] = json.dumps(tracked[:200], ensure_ascii=False)
    mark_dirty(data, SHEET_CONFIG)


def _get_tracked_bot_post_keys(data: dict[str, Any]) -> list[str]:
    raw = data.get("config", {}).get(CONFIG_TRACKED_BOT_POST_KEYS, "")
    if isinstance(raw, list):
        return [str(value) for value in raw if str(value)]
    if not raw:
        return []
    try:
        parsed = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(value) for value in parsed if str(value)]


if __name__ == "__main__":
    asyncio.run(main())
