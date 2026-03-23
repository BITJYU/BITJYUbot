# Band Bot

네이버 밴드 Open API와 Google Sheets를 이용해 동작하는 자동화 봇입니다.

현재 구조는 다음 원칙을 기준으로 동작합니다.

- 봇은 `자신이 작성한 게시글`의 댓글만 읽습니다.
- 사용자 명령은 댓글의 `[명령어/옵션]` 형식만 처리합니다.
- 골드 지급/차감 같은 관리자 보정은 명령어가 아니라 Google Sheets에서 직접 수정합니다.
- 데이터는 실행 시작 시 Google Sheets에서 한 번 읽고, 실행 종료 시 변경된 시트만 다시 저장합니다.

## Current Scope

현재 구현된 범위:

- 랜덤 명령어
  - `[주사위/XdY+Z]`
  - `[YN]`
  - `[선택/A/B/C]`
  - `[동전]`
- 경제 명령어
  - `[잔액]`
  - `[상점]`
  - `[구매/아이템명/수량]`
  - `[인벤토리]`
- 출석
  - `[출석]`
- 랜덤 목록 기반 명령
  - `[운세]`
  - `[뽑기]`
  - `[도박/금액]`

현재 보류된 범위:

- `[사용]`
- `[양도]`
- 전투 시스템

## Operation Model

주기 실행 봇:

- 최근 게시글을 조회합니다.
- 그중 `BOT_USER_ID`가 작성한 게시글만 감시 대상으로 봅니다.
- 감시 대상 게시글의 댓글만 조회합니다.
- 아직 처리하지 않은 댓글에서 `[명령어]`를 찾습니다.
- 답글 등록에 성공했을 때만 `처리내역`에 기록합니다.

일일 스케줄러:

- 매일 명령 게시글을 하나 작성할 수 있습니다.
- 예약 게시글이 있으면 함께 발송합니다.
- 생성된 봇 게시글 `post_key`는 `TRACKED_BOT_POST_KEYS`로 관리됩니다.

## Repository Layout

```text
BandBot/
├── .github/workflows/
│   ├── bot_a.yml
│   ├── bot_a_scheduler.yml
│   ├── bot_b.yml
│   └── bot_b_scheduler.yml
├── bot/
│   ├── band_api.py
│   ├── config.py
│   ├── dispatcher.py
│   ├── game_utils.py
│   ├── logging_utils.py
│   ├── main.py
│   ├── sheets.py
│   ├── utils.py
│   └── commands/
│       ├── attend_cmd.py
│       ├── battle_cmd.py
│       ├── economy_cmd.py
│       ├── gacha_cmd.py
│       └── random_cmd.py
├── callback.html
├── requirements.txt
└── scheduler.py
```
