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

## Google Sheets Tabs

현재 기준으로 먼저 준비해야 하는 시트는 아래 8개입니다.

### `설정`

헤더:

```text
키 | 값
```

권장 키:

```text
출석보상
COMMAND_POST_ENABLED
COMMAND_POST_CONTENT
CURRENT_COMMAND_POST_KEY
CURRENT_COMMAND_POST_CREATED_AT
TRACKED_BOT_POST_KEYS
```

예시:

```text
출석보상 | 100
COMMAND_POST_ENABLED | true
COMMAND_POST_CONTENT | 오늘의 명령 게시글입니다. 이 게시글 댓글에 [잔액], [상점], [출석] 등을 입력하세요.
TRACKED_BOT_POST_KEYS | []
```

### `목록`

유저 기본 정보와 스탯을 관리합니다.

```text
user_id | 닉네임 | HP | ATK | DEF | SPD | MP
```

### `인벤토리`

유저 골드와 아이템을 함께 관리합니다.

```text
user_id | 닉네임 | 골드 | 아이템명 | 수량 | 내구도 | 마지막업데이트
```

주의:

- 한 유저가 여러 아이템을 가지면 여러 행을 사용합니다.
- 아이템이 없어도 골드 저장을 위해 최소 1행은 유지하는 것이 안전합니다.

### `상점`

```text
아이템ID | 아이템명 | 가격 | 설명 | 재고 | 이미지URL
```

### `구매내역`

```text
user_id | 닉네임 | 아이템명 | 수량 | 가격 | 구매시각
```

### `출석`

```text
user_id | 닉네임 | 마지막출석일 | 연속출석일수
```

### `랜덤`

```text
항목
```

### `처리내역`

```text
ID | 타입 | 처리시각
```

선택 시트:

- `조사목록`
- `스킬목록`
- `전투상태`

## Secrets

GitHub 저장소의 `Settings > Secrets and variables > Actions > Repository secrets` 에 아래 값을 등록합니다.

봇 A:

- `BAND_ACCESS_TOKEN_A`
- `BAND_KEY_A`
- `GOOGLE_CREDENTIALS_A`
- `SHEET_URL_A`
- `BOT_NAME_A`
- `BOT_USER_ID_A`

봇 B:

- `BAND_ACCESS_TOKEN_B`
- `BAND_KEY_B`
- `GOOGLE_CREDENTIALS_B`
- `SHEET_URL_B`
- `BOT_NAME_B`
- `BOT_USER_ID_B`

`SHEET_URL` 사용을 권장합니다. `SHEET_NAME`은 현재 워크플로에 fallback 용도로 남아 있습니다.

## Workflows

주기 실행:

- [bot_a.yml](/c:/Users/whtna/OneDrive/Desktop/BandBot/.github/workflows/bot_a.yml)
- [bot_b.yml](/c:/Users/whtna/OneDrive/Desktop/BandBot/.github/workflows/bot_b.yml)

역할:

- 10분마다 실행
- 봇이 작성한 게시글의 댓글만 처리

스케줄러:

- [bot_a_scheduler.yml](/c:/Users/whtna/OneDrive/Desktop/BandBot/.github/workflows/bot_a_scheduler.yml)
- [bot_b_scheduler.yml](/c:/Users/whtna/OneDrive/Desktop/BandBot/.github/workflows/bot_b_scheduler.yml)

역할:

- 일일 명령 게시글 작성
- 예약 게시글 발송

## Redirect URI

BAND 앱 등록 시 OAuth Redirect URI가 필요하다면 GitHub Pages의 `callback.html`을 사용할 수 있습니다.

예시:

```text
https://<github-id>.github.io/<repo-name>/callback.html
```

저장소 루트의 [callback.html](/c:/Users/whtna/OneDrive/Desktop/BandBot/callback.html) 파일이 그 용도입니다.

## Notes

- 관리자 명령어는 사용하지 않습니다.
- 골드 지급/차감과 수동 보정은 Google Sheets에서 직접 수정합니다.
- 현재 메인 루프는 최근 게시글 조회 결과에서 새 봇 게시글을 발견하고, 이후에는 `TRACKED_BOT_POST_KEYS`를 통해 계속 감시합니다.
- 전투 시스템은 후순위입니다.
