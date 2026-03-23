"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class AppConfig:
    band_access_token: str
    band_key: str
    google_credentials: str
    sheet_name: str
    sheet_url: str
    bot_name: str
    bot_user_id: str
    admin_ids: set[str]
    attendance_gold: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        admin_ids_raw = os.environ.get("ADMIN_IDS", "")
        return cls(
            band_access_token=os.environ["BAND_ACCESS_TOKEN"],
            band_key=os.environ["BAND_KEY"],
            google_credentials=os.environ["GOOGLE_CREDENTIALS"],
            sheet_name=os.environ.get("SHEET_NAME", ""),
            sheet_url=os.environ.get("SHEET_URL", ""),
            bot_name=os.environ.get("BOT_NAME") or "\ubd07",
            bot_user_id=os.environ.get("BOT_USER_ID", ""),
            admin_ids={value.strip() for value in admin_ids_raw.split(",") if value.strip()},
            attendance_gold=int(os.environ.get("ATTENDANCE_GOLD", "100")),
        )
