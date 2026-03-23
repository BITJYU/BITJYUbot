# Band Bot

Naver Band automation bot project skeleton.

## Secrets

Set these in GitHub Actions secrets for each bot:

- `BAND_ACCESS_TOKEN_A`, `BAND_KEY_A`, `GOOGLE_CREDENTIALS_A`, `SHEET_URL_A`, `BOT_NAME_A`, `BOT_USER_ID_A`, `ADMIN_IDS_A`
- `BAND_ACCESS_TOKEN_B`, `BAND_KEY_B`, `GOOGLE_CREDENTIALS_B`, `SHEET_URL_B`, `BOT_NAME_B`, `BOT_USER_ID_B`, `ADMIN_IDS_B`

`SHEET_URL` is preferred over `SHEET_NAME`.

## Structure

- `.github/workflows/`
- `bot/`
- `bot/commands/`
- `scheduler.py`

## Status

Project scaffold created.
Implementation will be added step by step.
