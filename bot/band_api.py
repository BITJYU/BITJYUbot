"""Common Naver Band API helpers."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .config import AppConfig
from .logging_utils import log_error, log_warning

BASE_URL = "https://openapi.band.us"
LOCALE = "ko_KR"


async def band_api_call(
    session: aiohttp.ClientSession,
    method: str,
    endpoint: str,
    params: dict[str, Any],
    max_retries: int = 5,
) -> dict[str, Any] | None:
    """Call the Band Open API with exponential backoff."""
    delay = 1
    url = f"{BASE_URL}{endpoint}"
    http_method = method.upper()

    for attempt in range(max_retries):
        try:
            request = session.get if http_method == "GET" else session.post
            request_kwargs: dict[str, Any] = {}
            if http_method == "GET":
                request_kwargs["params"] = params
            else:
                request_kwargs["data"] = params

            async with request(url, **request_kwargs) as response:
                if response.status == 200:
                    return await response.json()

                if response.status == 429:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    log_error("Band API rate limit exceeded after retries.")
                    return None

                if response.status in (401, 403):
                    log_error(
                        f"[CRITICAL] Band API \uc778\uc99d \uc2e4\ud328 (HTTP {response.status}). "
                        "Access Token\uc774 \ub9cc\ub8cc\ub418\uc5c8\uc744 \uc218 \uc788\uc2b5\ub2c8\ub2e4.\n"
                        "GitHub Secrets\uc5d0\uc11c BAND_ACCESS_TOKEN\uc744 \uac31\uc2e0\ud574\uc8fc\uc138\uc694."
                    )
                    return None

                body = await _safe_read_text(response)
                log_error(f"Band API HTTP {response.status}: {body}")
                return None
        except aiohttp.ClientError as exc:
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            log_error(f"Band API client error: {exc}")
            return None
        except Exception as exc:
            log_error(f"Unexpected Band API error: {exc}")
            return None

    return None


async def get_posts(
    session: aiohttp.ClientSession,
    config: AppConfig,
    after: str | None = None,
    limit: int = 20,
) -> dict[str, Any] | None:
    params: dict[str, Any] = {
        "access_token": config.band_access_token,
        "band_key": config.band_key,
        "locale": LOCALE,
        "limit": limit,
    }
    if after:
        params["after"] = after
    return await band_api_call(session, "GET", "/v2/band/posts", params)


async def get_comments(
    session: aiohttp.ClientSession,
    config: AppConfig,
    post_key: str,
) -> dict[str, Any] | None:
    params = {
        "access_token": config.band_access_token,
        "band_key": config.band_key,
        "post_key": post_key,
        "locale": LOCALE,
    }
    return await band_api_call(session, "GET", "/v2/band/post/comments", params)


async def create_post(
    session: aiohttp.ClientSession,
    config: AppConfig,
    content: str,
) -> bool:
    params = {
        "access_token": config.band_access_token,
        "band_key": config.band_key,
        "content": content,
    }
    response = await band_api_call(session, "POST", "/v2/band/post/create", params)
    return bool(response and response.get("result_data"))


async def post_comment(
    session: aiohttp.ClientSession,
    config: AppConfig,
    post_key: str,
    body: str,
) -> bool:
    params = {
        "access_token": config.band_access_token,
        "band_key": config.band_key,
        "post_key": post_key,
        "body": body,
    }
    response = await band_api_call(session, "POST", "/v2/band/post/comment/create", params)
    if not response:
        log_warning(f"Failed to create comment for post {post_key[:8]}****")
        return False
    return bool(response.get("result_data"))


async def _safe_read_text(response: aiohttp.ClientResponse) -> str:
    try:
        return await response.text()
    except Exception:
        return "<unreadable response>"
