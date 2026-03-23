"""Google Sheets loading and dirty-write helpers."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from .config import AppConfig
from .logging_utils import log_error, log_info
from .utils import parse_iso_datetime, utc_now

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_CONFIG = "\uc124\uc815"
SHEET_USERS = "\uc720\uc800\uc794\uc561"
SHEET_INVENTORY = "\uc720\uc800\uc778\ubca4\ud1a0\ub9ac"
SHEET_STATS = "\uc720\uc800\uc2a4\ud0ef"
SHEET_SHOP = "\uc0c1\uc810\ubaa9\ub85d"
SHEET_SKILLS = "\uc2a4\ud0ac\ubaa9\ub85d"
SHEET_BATTLES = "\uc804\ud22c\uc0c1\ud0dc"
SHEET_PURCHASE_LOG = "\uad6c\ub9e4\ub0b4\uc5ed"
SHEET_ATTENDANCE = "\ucd9c\uc11d\ub0b4\uc5ed"
SHEET_SCHEDULED_POSTS = "\uc870\uc0ac\ubaa9\ub85d"
SHEET_RANDOM = "\ub79c\ub364\ubaa9\ub85d"
SHEET_PROCESSED = "\ucc98\ub9ac\ub0b4\uc5ed"

SHEET_NAMES = [
    SHEET_CONFIG,
    SHEET_USERS,
    SHEET_INVENTORY,
    SHEET_STATS,
    SHEET_SHOP,
    SHEET_SKILLS,
    SHEET_BATTLES,
    SHEET_PURCHASE_LOG,
    SHEET_ATTENDANCE,
    SHEET_SCHEDULED_POSTS,
    SHEET_RANDOM,
    SHEET_PROCESSED,
]

COL_KEY = "\ud0a4"
COL_VALUE = "\uac12"
COL_ITEM = "\ud56d\ubaa9"
COL_SKILL_NAME = "\uc2a4\ud0ac\uba85"
COL_BATTLE_ID = "\uc804\ud22cID"
COL_TEAM_A = "\ud300A"
COL_TEAM_B = "\ud300B"
COL_CURRENT_HP = "\ud604\uc7acHP"
COL_MAX_HP = "\ucd5c\ub300HP"
COL_CURRENT_MP = "\ud604\uc7acMP"
COL_TURN_ORDER = "\ud134\uc21c\uc11c"
COL_DEFENDING = "\ubc29\uc5b4\uc911"
COL_TURN_INDEX = "\ud604\uc7ac\ud134\uc778\ub371\uc2a4"
COL_STATUS = "\uc9c4\ud589\uc0c1\ud0dc"
COL_LAST_ACTION_TIME = "\ub9c8\uc9c0\ub9c9\ud589\ub3d9\uc2dc\uac01"
COL_PROCESSED_TYPE = "\ud0c0\uc785"
COL_PROCESSED_AT = "\ucc98\ub9ac\uc2dc\uac01"


def load_all_data(config: AppConfig) -> dict[str, Any]:
    """Load all configured sheets into memory once per run."""
    spreadsheet = _open_spreadsheet(config)

    worksheets = {}
    for sheet_name in SHEET_NAMES:
        try:
            worksheets[sheet_name] = spreadsheet.worksheet(sheet_name)
        except Exception as exc:
            log_error(f"Failed to access sheet '{sheet_name}': {exc}")
            raise

    raw_records = {name: worksheets[name].get_all_records() for name in SHEET_NAMES}
    data = {
        "config": _parse_config_rows(raw_records[SHEET_CONFIG]),
        "users": _parse_user_rows(raw_records[SHEET_USERS]),
        "inventory": _parse_inventory_rows(raw_records[SHEET_INVENTORY]),
        "stats": _parse_stats_rows(raw_records[SHEET_STATS]),
        "shop": _parse_shop_rows(raw_records[SHEET_SHOP]),
        "skills": _parse_skill_rows(raw_records[SHEET_SKILLS]),
        "battles": _parse_battle_rows(raw_records[SHEET_BATTLES]),
        "purchase_log": list(raw_records[SHEET_PURCHASE_LOG]),
        "attendance": _parse_attendance_rows(raw_records[SHEET_ATTENDANCE]),
        "scheduled_posts": list(raw_records[SHEET_SCHEDULED_POSTS]),
        "random_list": _parse_random_rows(raw_records[SHEET_RANDOM]),
        "processed": {row.get("ID", "") for row in raw_records[SHEET_PROCESSED] if row.get("ID")},
        "_processed_rows": list(raw_records[SHEET_PROCESSED]),
        "_worksheets": worksheets,
        "_dirty": set(),
    }
    log_info("Google Sheets data loaded into memory.")
    return data


def save_dirty_data(data: dict[str, Any]) -> None:
    """Write only changed sheet data back to Google Sheets."""
    dirty = set(data.get("_dirty", set()))
    if not dirty:
        return

    worksheet_map = data["_worksheets"]

    for sheet_name in dirty:
        if sheet_name == SHEET_USERS:
            _rewrite_sheet(worksheet_map[sheet_name], _serialize_users(data))
        elif sheet_name == SHEET_INVENTORY:
            _rewrite_sheet(worksheet_map[sheet_name], _serialize_inventory(data))
        elif sheet_name == SHEET_STATS:
            _rewrite_sheet(worksheet_map[sheet_name], _serialize_stats(data))
        elif sheet_name == SHEET_BATTLES:
            _rewrite_sheet(worksheet_map[sheet_name], _serialize_battles(data))
        elif sheet_name == SHEET_PURCHASE_LOG:
            _rewrite_sheet(worksheet_map[sheet_name], data.get("purchase_log", []))
        elif sheet_name == SHEET_ATTENDANCE:
            _rewrite_sheet(worksheet_map[sheet_name], _serialize_attendance(data))
        elif sheet_name == SHEET_SCHEDULED_POSTS:
            _rewrite_sheet(worksheet_map[sheet_name], data.get("scheduled_posts", []))
        elif sheet_name == SHEET_PROCESSED:
            _rewrite_sheet(worksheet_map[sheet_name], data.get("_processed_rows", []))
        elif sheet_name == SHEET_CONFIG:
            _rewrite_sheet(worksheet_map[sheet_name], _serialize_config(data))
        elif sheet_name == SHEET_SHOP:
            _rewrite_sheet(worksheet_map[sheet_name], data.get("shop", []))
        elif sheet_name == SHEET_SKILLS:
            _rewrite_sheet(worksheet_map[sheet_name], _serialize_skills(data))
        elif sheet_name == SHEET_RANDOM:
            _rewrite_sheet(
                worksheet_map[sheet_name],
                [{COL_ITEM: value} for value in data.get("random_list", [])],
            )

    data["_dirty"].clear()
    log_info("Dirty Google Sheets data flushed.")


def is_processed(data: dict[str, Any], key: str) -> bool:
    return key in data.get("processed", set())


def mark_processed(data: dict[str, Any], key: str, key_type: str) -> None:
    if not key or key in data.get("processed", set()):
        return

    timestamp = utc_now().isoformat()
    data["processed"].add(key)
    data.setdefault("_processed_rows", []).append(
        {"ID": key, COL_PROCESSED_TYPE: key_type, COL_PROCESSED_AT: timestamp}
    )
    data["_dirty"].add(SHEET_PROCESSED)


def cleanup_processed_records(data: dict[str, Any], retention_days: int = 7) -> int:
    cutoff = utc_now() - timedelta(days=retention_days)
    kept_rows = []

    for row in data.get("_processed_rows", []):
        processed_at = parse_iso_datetime(row.get(COL_PROCESSED_AT, ""))
        if processed_at and processed_at < cutoff:
            continue
        kept_rows.append(row)

    removed_count = len(data.get("_processed_rows", [])) - len(kept_rows)
    if removed_count:
        data["_processed_rows"] = kept_rows
        data["processed"] = {row.get("ID", "") for row in kept_rows if row.get("ID")}
        data["_dirty"].add(SHEET_PROCESSED)

    return removed_count


def _open_spreadsheet(config: AppConfig) -> gspread.Spreadsheet:
    credentials_info = json.loads(config.google_credentials)
    credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
    client = gspread.authorize(credentials)
    if config.sheet_url:
        return client.open_by_url(config.sheet_url)
    if config.sheet_name:
        return client.open(config.sheet_name)
    raise ValueError("SHEET_URL or SHEET_NAME must be provided.")


def _rewrite_sheet(worksheet: gspread.Worksheet, records: list[dict[str, Any]]) -> None:
    if not records:
        worksheet.clear()
        return

    headers = list(records[0].keys())
    values = [headers]
    for record in records:
        values.append([record.get(header, "") for header in headers])
    worksheet.clear()
    worksheet.update(values)


def _parse_config_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {row.get(COL_KEY, ""): row.get(COL_VALUE, "") for row in rows if row.get(COL_KEY)}


def _parse_user_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    parsed = {}
    for row in rows:
        user_id = row.get("user_id")
        if user_id:
            parsed[user_id] = dict(row)
    return parsed


def _parse_inventory_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    parsed: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        user_id = row.get("user_id")
        if not user_id:
            continue
        parsed.setdefault(user_id, []).append(dict(row))
    return parsed


def _parse_stats_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    parsed = {}
    for row in rows:
        user_id = row.get("user_id")
        if user_id:
            parsed[user_id] = dict(row)
    return parsed


def _parse_shop_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _parse_skill_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    parsed = {}
    for row in rows:
        skill_name = row.get(COL_SKILL_NAME)
        if skill_name:
            parsed[skill_name] = dict(row)
    return parsed


def _parse_battle_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    parsed = {}
    for row in rows:
        battle_id = row.get(COL_BATTLE_ID)
        if not battle_id:
            continue
        parsed[battle_id] = {
            "battle_id": battle_id,
            "team_a": _json_or_default(row.get(COL_TEAM_A), []),
            "team_b": _json_or_default(row.get(COL_TEAM_B), []),
            "current_hp": _json_or_default(row.get(COL_CURRENT_HP), {}),
            "max_hp": _json_or_default(row.get(COL_MAX_HP), {}),
            "current_mp": _json_or_default(row.get(COL_CURRENT_MP), {}),
            "turn_order": _json_or_default(row.get(COL_TURN_ORDER), []),
            "defending": set(_json_or_default(row.get(COL_DEFENDING), [])),
            "current_turn_index": int(row.get(COL_TURN_INDEX, 0) or 0),
            "status": row.get(COL_STATUS, "\uc9c4\ud589\uc911"),
            "post_key": row.get("post_key", ""),
            "last_action_time": row.get(COL_LAST_ACTION_TIME, ""),
        }
    return parsed


def _parse_attendance_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    parsed = {}
    for row in rows:
        user_id = row.get("user_id")
        if user_id:
            parsed[user_id] = dict(row)
    return parsed


def _parse_random_rows(rows: list[dict[str, Any]]) -> list[str]:
    return [row.get(COL_ITEM, "") for row in rows if row.get(COL_ITEM)]


def _serialize_config(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [{COL_KEY: key, COL_VALUE: value} for key, value in data.get("config", {}).items()]


def _serialize_users(data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(data.get("users", {}).values())


def _serialize_inventory(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for items in data.get("inventory", {}).values():
        rows.extend(items)
    return rows


def _serialize_stats(data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(data.get("stats", {}).values())


def _serialize_skills(data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(data.get("skills", {}).values())


def _serialize_battles(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for battle in data.get("battles", {}).values():
        rows.append(
            {
                COL_BATTLE_ID: battle.get("battle_id", ""),
                COL_TEAM_A: json.dumps(battle.get("team_a", []), ensure_ascii=False),
                COL_TEAM_B: json.dumps(battle.get("team_b", []), ensure_ascii=False),
                COL_CURRENT_HP: json.dumps(battle.get("current_hp", {}), ensure_ascii=False),
                COL_MAX_HP: json.dumps(battle.get("max_hp", {}), ensure_ascii=False),
                COL_CURRENT_MP: json.dumps(battle.get("current_mp", {}), ensure_ascii=False),
                COL_TURN_ORDER: json.dumps(battle.get("turn_order", []), ensure_ascii=False),
                COL_DEFENDING: json.dumps(sorted(battle.get("defending", set())), ensure_ascii=False),
                COL_TURN_INDEX: battle.get("current_turn_index", 0),
                COL_STATUS: battle.get("status", "\uc9c4\ud589\uc911"),
                COL_LAST_ACTION_TIME: battle.get("last_action_time", ""),
                "post_key": battle.get("post_key", ""),
            }
        )
    return rows


def _serialize_attendance(data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(data.get("attendance", {}).values())


def _json_or_default(value: Any, default: Any) -> Any:
    if value in ("", None):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default
