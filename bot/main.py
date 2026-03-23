"""Main entry point for the Band bot."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

from .band_api import get_comments, get_posts, post_comment
from .config import AppConfig
from .dispatcher import dispatch_command, parse_command
from .logging_utils import log_error, log_info, log_warning, mask_identifier
from .sheets import cleanup_processed_records, is_processed, load_all_data, mark_processed, save_dirty_data

COMMENT_INTERVAL_SECONDS = 0.3
POST_FETCH_LIMIT = 20
PROCESSED_COMMENT_TYPE = "\ub313\uae00"
SHEET_CONFIG = "\uc124\uc815"
CONFIG_TRACKED_BOT_POST_KEYS = "TRACKED_BOT_POST_KEYS"
MAX_TRACKED_BOT_POSTS = 200


async def main() -> None:
    """Load data, process bot-authored post comments, then flush changes."""
    config = AppConfig.from_env()
    data = load_all_data(config)

    try:
        async with aiohttp.ClientSession() as session:
            await run_cycle(session, config, data)
    finally:
        save_dirty_data(data)


async def run_cycle(
    session: aiohttp.ClientSession,
    config: AppConfig,
    data: dict[str, Any],
) -> None:
    """Execute one polling cycle."""
    posts_response = await get_posts(session, config, limit=POST_FETCH_LIMIT)
    if not posts_response:
        log_warning("No posts response received from Band API.")
        cleanup_processed_records(data)
        return

    posts = extract_items(posts_response)
    tracked_post_keys = merge_tracked_bot_post_keys(data, config, posts)

    for post_key in tracked_post_keys:
        await process_post_comments(post_key, session, config, data)

    await check_battle_timeouts(session, config, data)
    removed = cleanup_processed_records(data)
    if removed:
        log_info(f"Removed {removed} expired processed record(s).")


async def process_post_comments(
    post_key: str,
    session: aiohttp.ClientSession,
    config: AppConfig,
    data: dict[str, Any],
) -> None:
    """Fetch and process comments for a bot-authored post."""
    if not post_key:
        return

    comments_response = await get_comments(session, config, post_key)
    if not comments_response:
        return

    comments = extract_items(comments_response)
    for comment in comments:
        await process_comment(comment, post_key, session, config, data)
        await asyncio.sleep(COMMENT_INTERVAL_SECONDS)


async def process_comment(
    comment: dict[str, Any],
    post_key: str,
    session: aiohttp.ClientSession,
    config: AppConfig,
    data: dict[str, Any],
) -> None:
    """Process a single comment with duplicate protection and reply atomicity."""
    comment_key = get_comment_key(comment)
    if not comment_key:
        return

    try:
        author_id = get_author_id(comment)
        if author_id and author_id == config.bot_user_id:
            return

        if is_processed(data, comment_key):
            return

        parsed = parse_command(get_text_body(comment))
        if not parsed:
            return

        result = await dispatch_command(parsed, build_actor_context(comment), data, post_key=post_key)
        if not result:
            return

        success = await post_comment(session, config, post_key, result)
        if success:
            mark_processed(data, comment_key, PROCESSED_COMMENT_TYPE)
    except Exception as exc:
        safe_key = mask_identifier(comment_key, visible=8)
        log_error(f"comment {safe_key}: {exc}")


async def check_battle_timeouts(
    session: aiohttp.ClientSession,
    config: AppConfig,
    data: dict[str, Any],
) -> None:
    """Placeholder for battle timeout checks to be implemented with battle logic."""
    _ = (session, config, data)


def extract_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    result_data = response.get("result_data", {})
    items = result_data.get("items", [])
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def is_bot_authored_post(post: dict[str, Any], config: AppConfig) -> bool:
    author_id = get_author_id(post)
    return bool(author_id and config.bot_user_id and author_id == config.bot_user_id)


def merge_tracked_bot_post_keys(
    data: dict[str, Any],
    config: AppConfig,
    posts: list[dict[str, Any]],
) -> list[str]:
    tracked = get_tracked_bot_post_keys(data)
    found = []

    for post in posts:
        if not is_bot_authored_post(post, config):
            continue
        post_key = get_post_key(post)
        if post_key:
            found.append(post_key)

    merged = _unique_preserving_order(found + tracked)
    merged = merged[:MAX_TRACKED_BOT_POSTS]
    if merged != tracked:
        data.setdefault("config", {})[CONFIG_TRACKED_BOT_POST_KEYS] = json.dumps(merged, ensure_ascii=False)
        data.setdefault("_dirty", set()).add(SHEET_CONFIG)
    return merged


def get_tracked_bot_post_keys(data: dict[str, Any]) -> list[str]:
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


def _unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def get_post_key(post: dict[str, Any]) -> str:
    return str(post.get("post_key", "") or "")


def get_comment_key(comment: dict[str, Any]) -> str:
    return str(comment.get("comment_key", "") or "")


def get_text_body(entry: dict[str, Any]) -> str:
    return str(entry.get("content", "") or entry.get("body", "") or "")


def get_author_id(entry: dict[str, Any]) -> str:
    author = entry.get("author", {})
    if isinstance(author, dict):
        return str(author.get("user_key", "") or author.get("user_id", "") or "")
    return ""


def get_author_name(entry: dict[str, Any]) -> str:
    author = entry.get("author", {})
    if isinstance(author, dict):
        return str(author.get("name", "") or "")
    return ""


def build_actor_context(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize post/comment payloads into a shared actor context shape."""
    return {
        "author_id": get_author_id(entry),
        "nickname": get_author_name(entry),
        "body": get_text_body(entry),
        "comment_key": get_comment_key(entry),
        "post_key": get_post_key(entry),
        "raw": entry,
    }


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("Band bot stopped by user.")
