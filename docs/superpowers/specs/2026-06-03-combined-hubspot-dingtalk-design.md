# Combined HubSpot → DingTalk Daily Report — Design

**Date:** 2026-06-03
**Status:** Approved (pending user review of this doc)

## Goal

Merge `check_industry.py` and `send_custom_robot_group_message.py` into a single daily-cron-friendly script that pulls a HubSpot industry breakdown for two rolling windows and posts the result to a DingTalk group via a signed webhook. Credentials load from a local `.env` for development and from Render-managed environment variables in production.

## Scope

**In scope**
- One combined entry point (`daily_report.py`) that fetches data and posts to DingTalk.
- Two reporting windows in a single message: yesterday and week-to-date.
- Refactor the two existing scripts so their core logic moves into reusable modules.
- `.env` and `.env.example` config; `.gitignore`; `requirements.txt`.
- `render.yaml` for Render cron deployment.

**Out of scope** (YAGNI)
- Charts/images in DingTalk messages.
- Persisting history to a database.
- @-mentioning users.
- Multi-group routing.
- Backfill / arbitrary date-range mode.
- An end-to-end test against real HubSpot or DingTalk.

## Tech stack

- Python 3.10+ (uses `str | None` syntax already present in `check_industry.py`).
- `requests` for HTTP.
- `python-dotenv` for local env loading.
- `zoneinfo` (stdlib) for SGT.
- `pytest` for the unit tests.

## Architecture

### File layout

```
industry-checker/
├── .env                          # local secrets, gitignored
├── .env.example                  # committed template
├── .gitignore
├── README.md
├── render.yaml
├── requirements.txt
├── hubspot_client.py             # HubSpot fetch + summarize (pure functions)
├── dingtalk_client.py            # DingTalk send (pure function)
├── report.py                     # format breakdown into text
├── daily_report.py               # combined cron entry point
├── check_industry.py             # existing CLI, refactored to import hubspot_client + report
├── send_custom_robot_group_message.py   # existing CLI, refactored to import dingtalk_client
└── tests/
    ├── __init__.py
    ├── test_hubspot_client.py
    ├── test_dingtalk_client.py
    ├── test_report.py
    └── test_daily_report.py
```

### Modules and their boundaries

#### `hubspot_client.py`

Two pure functions. No argparse, no printing, no `load_dotenv` at import time.

```python
def fetch_contacts(start_ms: int, end_ms: int, properties: list[str]) -> list[dict]: ...

def summarize_industry(contacts: list[dict]) -> dict:
    # returns {"total": int, "with_industry": int, "distribution": [{"name", "count", "percent"}, ...]}
```

- `fetch_contacts` reads `HUBSPOT_PRIVATE_APP_TOKEN` from `os.environ` at call time. Raises `RuntimeError("HUBSPOT_PRIVATE_APP_TOKEN is not set")` if missing.
- Same paging / filter logic as today (`createdate` between GTE/LTE, `bot_status HAS_PROPERTY`, sorted ascending, limit 100).
- `summarize_industry` keeps the existing semantics: percent is over `with_industry`, sorted desc by count.

#### `dingtalk_client.py`

One pure function. No argparse, no logger setup at import time.

```python
def send_message(access_token: str, secret: str, msg: str) -> dict: ...
```

- Signed-webhook logic moved verbatim from existing CLI.
- POSTs to `https://oapi.dingtalk.com/robot/send?access_token=...&timestamp=...&sign=...`.
- Body shape unchanged: `{"msgtype": "text", "text": {"content": msg}, "at": {...}}`.
- Drops the `at_user_ids` / `at_mobiles` / `is_at_all` parameters from the public function signature — the daily report doesn't @-mention anyone. (They live on in the standalone CLI.)
- Raises on non-200 HTTP. Also raises if response JSON has non-zero `errcode`, surfacing `errmsg`.

#### `report.py`

```python
def format_section(label: str, summary: dict) -> str: ...
```

Produces lines like:

```
=== Industry breakdown: <label> ===
Total contacts created: N
With industry filled:   M

  IndustryA   12   45.5%
  IndustryB    3   11.5%
  ...
```

Empty case (`summary["total"] == 0`):

```
=== Industry breakdown: <label> ===
(no contacts in this window)
```

#### `daily_report.py`

Combined entry point. Responsibilities:

1. `load_dotenv(SCRIPT_DIR / ".env")` — no-op on Render where the file is absent.
2. `compute_windows(now_sgt: datetime) -> list[tuple[str, int | None, int | None]]` — returns two `(label, start_ms, end_ms)` tuples. Both can be `None` when the window is invalid (week just started).
3. Fetch each valid window via `hubspot_client.fetch_contacts`.
4. Summarize each via `hubspot_client.summarize_industry`.
5. Format each via `report.format_section`. For invalid windows produce a `(week just started — no data yet)` line.
6. Join sections with `\n\n` and call `dingtalk_client.send_message`.
7. Print the message to stdout too, so Render logs show what was posted.

Timezone: `Asia/Singapore`. All window boundaries computed in SGT and converted to UTC ms for the HubSpot API.

`compute_windows` definitions (given `now_sgt` at 09:00 on date `D`):

- **Yesterday**: start = `D-1 00:00 SGT`, end = `D-1 23:59:59.999 SGT`.
- **WTD**: `monday_of_this_week = D - timedelta(days=D.weekday())`. If `monday_of_this_week > D-1`, mark invalid (both ms values `None`). Else start = `monday_of_this_week 00:00 SGT`, end = `D-1 23:59:59.999 SGT`.

Labels:

- `"2026-06-02 (yesterday)"`
- `"2026-06-01 to 2026-06-02 (WTD)"` or `"2026-06-02 (WTD)"` if single-day

#### `check_industry.py` (refactored)

Behavior preserved: prints a single-window breakdown for `START_DATE`/`END_DATE` constants at the top of the file. Now imports `fetch_contacts`, `summarize_industry` from `hubspot_client`, and `format_section` from `report`. The duplicate fetch + summarize logic is removed.

#### `send_custom_robot_group_message.py` (refactored)

Behavior preserved: argparse CLI with `--access_token`, `--secret`, `--msg`, `--userid`, `--at_mobiles`, `--is_at_all`. Imports `send_message` from `dingtalk_client`. The @-mention args are handled in this CLI by building a richer body locally (not in the module).

## Data flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Render Cron Job (or local run)                                  │
│                                                                 │
│  python daily_report.py                                         │
│       │                                                         │
│       ▼                                                         │
│  compute_windows(now_sgt)  ──▶ [yesterday, WTD]                 │
│       │                                                         │
│       ▼                                                         │
│  for each window:                                               │
│    hubspot_client.fetch_contacts() ──HTTPS──▶ HubSpot API       │
│    hubspot_client.summarize_industry()                          │
│    report.format_section()                                      │
│       │                                                         │
│       ▼                                                         │
│  "\n\n".join(sections)                                          │
│       │                                                         │
│       ▼                                                         │
│  dingtalk_client.send_message() ──HTTPS──▶ DingTalk webhook     │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

### `.env` (local) and Render environment variables (prod)

| Variable | Source | Purpose |
|---|---|---|
| `HUBSPOT_PRIVATE_APP_TOKEN` | HubSpot private app | Bearer token for the contact search API |
| `DINGTALK_ACCESS_TOKEN` | DingTalk custom robot webhook URL | The `access_token` query param |
| `DINGTALK_SECRET` | DingTalk custom robot security settings | HMAC signing secret |

### `.env.example`

```
HUBSPOT_PRIVATE_APP_TOKEN=pat-xxxxxxxxxxxxxxxxxx
DINGTALK_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DINGTALK_SECRET=SECxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### `.gitignore`

```
.env
__pycache__/
*.pyc
.pytest_cache/
```

### `render.yaml`

```yaml
services:
  - type: cron
    name: industry-checker-daily
    runtime: python
    schedule: "0 1 * * *"   # 09:00 SGT
    buildCommand: pip install -r requirements.txt
    startCommand: python daily_report.py
    envVars:
      - key: HUBSPOT_PRIVATE_APP_TOKEN
        sync: false
      - key: DINGTALK_ACCESS_TOKEN
        sync: false
      - key: DINGTALK_SECRET
        sync: false
```

`sync: false` means values aren't committed; set them in the Render dashboard.

### `requirements.txt`

```
requests>=2.31
python-dotenv>=1.0
```

## Example output message

```
=== Industry breakdown: 2026-06-02 (yesterday) ===
Total contacts created: 14
With industry filled:   11

  Manufacturing    5   45.5%
  F&B              3   27.3%
  Retail           2   18.2%
  Logistics        1    9.1%

=== Industry breakdown: 2026-06-01 to 2026-06-02 (WTD) ===
Total contacts created: 27
With industry filled:   21

  Manufacturing   10   47.6%
  F&B              6   28.6%
  Retail           3   14.3%
  Logistics        2    9.5%
```

## Error handling

- **Missing env var** — raise `RuntimeError("<VAR> is not set")` at the point of use. Render surfaces the traceback in cron logs.
- **HubSpot API non-2xx** — `requests.Response.raise_for_status()` propagates. No retries (Render reruns the cron tomorrow; a one-off blip is fine).
- **DingTalk non-2xx or non-zero errcode** — raise `RuntimeError(f"DingTalk error: {errmsg}")`. The HubSpot work already succeeded so we still print the would-be message to stdout for log capture.
- **No contacts in a window** — not an error; the section renders the empty-window line.

## Testing strategy

Unit tests only. No live HubSpot or DingTalk calls. Each test file targets one module.

### `tests/test_hubspot_client.py`
- `test_summarize_industry_basic` — three contacts with two distinct industries; verify counts, percent, sort.
- `test_summarize_industry_strips_whitespace` — `"  F&B  "` and `"F&B"` collapse to one bucket.
- `test_summarize_industry_excludes_blank` — empty/missing `your_industry` excluded from `with_industry` and distribution.
- `test_summarize_industry_empty` — empty list returns `{"total": 0, "with_industry": 0, "distribution": []}`.
- `test_fetch_contacts_raises_without_token` — `monkeypatch.delenv("HUBSPOT_PRIVATE_APP_TOKEN", raising=False)`, expect `RuntimeError`.
- `test_fetch_contacts_pagination` — mock `requests.post` to return two pages; verify all contacts merged and `after` cursor sent on page 2.

### `tests/test_dingtalk_client.py`
- `test_send_message_signs_request` — mock `requests.post`; assert URL contains `access_token`, `timestamp`, and a non-empty `sign`. Verify body matches expected shape.
- `test_send_message_raises_on_errcode` — mock response with `{"errcode": 310000, "errmsg": "keywords not in content"}`; expect `RuntimeError` containing `"keywords not in content"`.

### `tests/test_report.py`
- `test_format_section_with_data` — sample summary, assert label line, totals, and three industry rows present and aligned.
- `test_format_section_empty` — `total=0` produces the `(no contacts in this window)` line.

### `tests/test_daily_report.py`
- `test_compute_windows_midweek` — `now_sgt = Wed 2026-06-03 09:00`. Expect yesterday = 2026-06-02, WTD = 2026-06-01 to 2026-06-02. Verify ms boundaries are SGT 00:00 / 23:59:59.999 converted to UTC.
- `test_compute_windows_monday_morning` — `now_sgt = Mon 2026-06-08 09:00`. Expect yesterday = 2026-06-07; WTD marked invalid (this week's Monday is today).

## Deployment runbook (one-time)

1. Push the repo to GitHub.
2. In Render dashboard: New → Cron Job → connect repo → Render reads `render.yaml`.
3. In the Render service's Environment tab, set `HUBSPOT_PRIVATE_APP_TOKEN`, `DINGTALK_ACCESS_TOKEN`, `DINGTALK_SECRET`.
4. Trigger a manual run from the dashboard to confirm the DingTalk group receives the message.
5. Cron then fires daily at `0 1 * * *` UTC.

## Open questions

None — all design decisions resolved during brainstorming.
