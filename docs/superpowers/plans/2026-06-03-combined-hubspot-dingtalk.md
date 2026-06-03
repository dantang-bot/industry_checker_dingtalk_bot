# Combined HubSpot → DingTalk Daily Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Combine the existing HubSpot industry checker and DingTalk webhook sender into a single daily-cron script that posts a yesterday + WTD industry breakdown to a DingTalk group, deployable to Render via `render.yaml`.

**Architecture:** Three pure-function modules (`hubspot_client`, `dingtalk_client`, `report`) with a thin orchestrator (`daily_report.py`). The two existing CLIs are refactored to import from these modules so behavior is preserved. Credentials load from `.env` locally and from Render-managed env vars in production.

**Tech Stack:** Python 3.10+, `requests`, `python-dotenv`, `pytest`, stdlib `zoneinfo`. Render cron service.

**Related spec:** `docs/superpowers/specs/2026-06-03-combined-hubspot-dingtalk-design.md`

---

## Pre-flight

The project directory `/Users/dan/work/industry-checker` exists but is **not** a git repository. Tasks below assume each step's commit lands in that repo, so the very first task initializes git. If the working directory already has a `.git/` directory, skip Task 0 step 1.

The two existing files (`check_industry.py`, `send_custom_robot_group_message.py`) will be modified later in the plan, not at the start. Leave them alone until the relevant task.

---

## Task 0: Initialize project scaffolding

**Files:**
- Create: `/Users/dan/work/industry-checker/.gitignore`
- Create: `/Users/dan/work/industry-checker/requirements.txt`
- Create: `/Users/dan/work/industry-checker/.env.example`
- Create: `/Users/dan/work/industry-checker/tests/__init__.py`
- Create: `/Users/dan/work/industry-checker/conftest.py`

- [ ] **Step 1: Initialize git repo (skip if `.git/` already exists)**

Run:
```bash
cd /Users/dan/work/industry-checker && git init && git branch -M main
```
Expected: `Initialized empty Git repository in /Users/dan/work/industry-checker/.git/`

- [ ] **Step 2: Write `.gitignore`**

Path: `/Users/dan/work/industry-checker/.gitignore`

```
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
```

- [ ] **Step 3: Write `requirements.txt`**

Path: `/Users/dan/work/industry-checker/requirements.txt`

```
requests>=2.31
python-dotenv>=1.0
pytest>=8.0
```

(Note: `pytest` ships in the same file because Render's cron build runs `pip install -r requirements.txt`; the extra dep is small and lets you run tests on the deployed environment if needed. If you want a cleaner split, use `requirements-dev.txt` — but for a one-person script this is fine.)

- [ ] **Step 4: Write `.env.example`**

Path: `/Users/dan/work/industry-checker/.env.example`

```
HUBSPOT_PRIVATE_APP_TOKEN=pat-xxxxxxxxxxxxxxxxxx
DINGTALK_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DINGTALK_SECRET=SECxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- [ ] **Step 5: Create empty `tests/__init__.py`**

Path: `/Users/dan/work/industry-checker/tests/__init__.py`

(Empty file. Marks `tests/` as a package.)

- [ ] **Step 6: Write `conftest.py` to clear env vars between tests**

Path: `/Users/dan/work/industry-checker/conftest.py`

```python
import os

import pytest


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for var in ("HUBSPOT_PRIVATE_APP_TOKEN", "DINGTALK_ACCESS_TOKEN", "DINGTALK_SECRET"):
        monkeypatch.delenv(var, raising=False)
```

This guards against test pollution from a developer's local `.env`.

- [ ] **Step 7: Create and activate a virtualenv, install deps**

Run:
```bash
cd /Users/dan/work/industry-checker && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
Expected: `Successfully installed ...` with `requests`, `python-dotenv`, `pytest` and their deps. No errors.

- [ ] **Step 8: Verify pytest discovers zero tests**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest -q
```
Expected: `no tests ran` (exit code 5 is fine here — it just means no tests yet).

- [ ] **Step 9: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add .gitignore requirements.txt .env.example tests/__init__.py conftest.py && git commit -m "chore: scaffold project (gitignore, deps, env template, tests dir)"
```

---

## Task 1: Extract `summarize_industry` into `hubspot_client.py`

This is the easier of the two `hubspot_client` functions because it's pure (no HTTP). Build it first to lock in the data shape.

**Files:**
- Create: `/Users/dan/work/industry-checker/hubspot_client.py`
- Create: `/Users/dan/work/industry-checker/tests/test_hubspot_client.py`

- [ ] **Step 1: Write failing tests for `summarize_industry`**

Path: `/Users/dan/work/industry-checker/tests/test_hubspot_client.py`

```python
import pytest

from hubspot_client import summarize_industry


def test_summarize_industry_basic():
    contacts = [
        {"your_industry": "Manufacturing"},
        {"your_industry": "Manufacturing"},
        {"your_industry": "F&B"},
    ]
    result = summarize_industry(contacts)
    assert result["total"] == 3
    assert result["with_industry"] == 3
    assert result["distribution"] == [
        {"name": "Manufacturing", "count": 2, "percent": pytest.approx(66.666, rel=1e-3)},
        {"name": "F&B", "count": 1, "percent": pytest.approx(33.333, rel=1e-3)},
    ]


def test_summarize_industry_strips_whitespace():
    contacts = [
        {"your_industry": "  F&B  "},
        {"your_industry": "F&B"},
    ]
    result = summarize_industry(contacts)
    assert result["with_industry"] == 2
    assert len(result["distribution"]) == 1
    assert result["distribution"][0]["name"] == "F&B"
    assert result["distribution"][0]["count"] == 2


def test_summarize_industry_excludes_blank():
    contacts = [
        {"your_industry": "Manufacturing"},
        {"your_industry": ""},
        {"your_industry": None},
        {},
    ]
    result = summarize_industry(contacts)
    assert result["total"] == 4
    assert result["with_industry"] == 1
    assert result["distribution"] == [
        {"name": "Manufacturing", "count": 1, "percent": 100.0},
    ]


def test_summarize_industry_empty():
    result = summarize_industry([])
    assert result == {"total": 0, "with_industry": 0, "distribution": []}
```

- [ ] **Step 2: Run the tests, expect failure**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_hubspot_client.py -v
```
Expected: `ModuleNotFoundError: No module named 'hubspot_client'` — all four tests fail at collection.

- [ ] **Step 3: Implement `summarize_industry`**

Path: `/Users/dan/work/industry-checker/hubspot_client.py`

```python
"""HubSpot client: fetch contacts in a date window and summarize industry distribution."""
from collections import Counter


def summarize_industry(contacts: list[dict]) -> dict:
    """Return {total, with_industry, distribution: [{name, count, percent}, ...]}.

    Percentages are over with_industry, not total. Distribution sorted desc by count.
    """
    with_industry = [c for c in contacts if (c.get("your_industry") or "").strip()]
    counter = Counter((c.get("your_industry") or "").strip() for c in with_industry)
    distribution = [
        {
            "name": name,
            "count": count,
            "percent": count / len(with_industry) * 100 if with_industry else 0,
        }
        for name, count in counter.most_common()
    ]
    return {
        "total": len(contacts),
        "with_industry": len(with_industry),
        "distribution": distribution,
    }
```

- [ ] **Step 4: Run tests, expect all four passing**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_hubspot_client.py -v
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add hubspot_client.py tests/test_hubspot_client.py && git commit -m "feat: extract summarize_industry into hubspot_client module"
```

---

## Task 2: Add `fetch_contacts` to `hubspot_client.py`

**Files:**
- Modify: `/Users/dan/work/industry-checker/hubspot_client.py`
- Modify: `/Users/dan/work/industry-checker/tests/test_hubspot_client.py`

- [ ] **Step 1: Add failing tests for `fetch_contacts`**

Append to `/Users/dan/work/industry-checker/tests/test_hubspot_client.py`:

```python
from unittest.mock import MagicMock, patch

from hubspot_client import fetch_contacts


def test_fetch_contacts_raises_without_token():
    with pytest.raises(RuntimeError, match="HUBSPOT_PRIVATE_APP_TOKEN"):
        fetch_contacts(1, 2, ["your_industry"])


def test_fetch_contacts_pagination(monkeypatch):
    monkeypatch.setenv("HUBSPOT_PRIVATE_APP_TOKEN", "fake-token")

    page1 = MagicMock()
    page1.json.return_value = {
        "results": [
            {"properties": {"your_industry": "Manufacturing"}},
            {"properties": {"your_industry": "F&B"}},
        ],
        "paging": {"next": {"after": "cursor-2"}},
    }
    page2 = MagicMock()
    page2.json.return_value = {
        "results": [
            {"properties": {"your_industry": "Retail"}},
        ],
    }

    with patch("hubspot_client.requests.post", side_effect=[page1, page2]) as post:
        result = fetch_contacts(1000, 2000, ["your_industry"])

    assert result == [
        {"your_industry": "Manufacturing"},
        {"your_industry": "F&B"},
        {"your_industry": "Retail"},
    ]
    assert post.call_count == 2

    first_call_payload = post.call_args_list[0].kwargs["json"]
    assert first_call_payload["limit"] == 100
    assert "after" not in first_call_payload
    second_call_payload = post.call_args_list[1].kwargs["json"]
    assert second_call_payload["after"] == "cursor-2"
```

- [ ] **Step 2: Run tests, expect failure**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_hubspot_client.py -v
```
Expected: 4 prior tests still pass, 2 new tests fail with `ImportError: cannot import name 'fetch_contacts'`.

- [ ] **Step 3: Implement `fetch_contacts`**

Append to `/Users/dan/work/industry-checker/hubspot_client.py`:

```python
import os

import requests


def fetch_contacts(start_ms: int, end_ms: int, properties: list[str]) -> list[dict]:
    """Fetch HubSpot contacts created in [start_ms, end_ms] with bot_status set.

    Returns flattened list of contact properties dicts, paginated through all results.
    """
    token = os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN")
    if not token:
        raise RuntimeError("HUBSPOT_PRIVATE_APP_TOKEN is not set")

    contacts: list[dict] = []
    after: str | None = None
    while True:
        payload: dict = {
            "filterGroups": [{
                "filters": [
                    {"propertyName": "createdate", "operator": "GTE", "value": str(start_ms)},
                    {"propertyName": "createdate", "operator": "LTE", "value": str(end_ms)},
                    {"propertyName": "bot_status", "operator": "HAS_PROPERTY"},
                ],
            }],
            "properties": properties,
            "limit": 100,
            "sorts": [{"propertyName": "createdate", "direction": "ASCENDING"}],
        }
        if after:
            payload["after"] = after

        resp = requests.post(
            "https://api.hubapi.com/crm/v3/objects/contacts/search",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        for r in data.get("results", []):
            contacts.append(r.get("properties", {}))

        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break

    return contacts
```

Move the `import os` and `import requests` to the top of the file alongside the existing imports for cleanliness. Final import block at the top:

```python
"""HubSpot client: fetch contacts in a date window and summarize industry distribution."""
import os
from collections import Counter

import requests
```

- [ ] **Step 4: Run tests, expect all six passing**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_hubspot_client.py -v
```
Expected: `6 passed`.

- [ ] **Step 5: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add hubspot_client.py tests/test_hubspot_client.py && git commit -m "feat: add fetch_contacts to hubspot_client with pagination"
```

---

## Task 3: Extract `send_message` into `dingtalk_client.py`

**Files:**
- Create: `/Users/dan/work/industry-checker/dingtalk_client.py`
- Create: `/Users/dan/work/industry-checker/tests/test_dingtalk_client.py`

- [ ] **Step 1: Write failing tests**

Path: `/Users/dan/work/industry-checker/tests/test_dingtalk_client.py`

```python
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from dingtalk_client import send_message


def test_send_message_signs_request():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}

    with patch("dingtalk_client.requests.post", return_value=mock_resp) as post:
        send_message("token-abc", "SECsecret", "hello group")

    assert post.call_count == 1
    call = post.call_args

    url = call.args[0]
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert params["access_token"] == ["token-abc"]
    assert "timestamp" in params and params["timestamp"][0].isdigit()
    assert "sign" in params and len(params["sign"][0]) > 0

    body = call.kwargs["json"]
    assert body["msgtype"] == "text"
    assert body["text"] == {"content": "hello group"}


def test_send_message_raises_on_errcode():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"errcode": 310000, "errmsg": "keywords not in content"}

    with patch("dingtalk_client.requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="keywords not in content"):
            send_message("token-abc", "SECsecret", "bad message")
```

- [ ] **Step 2: Run tests, expect failure**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_dingtalk_client.py -v
```
Expected: both tests fail at import with `ModuleNotFoundError: No module named 'dingtalk_client'`.

- [ ] **Step 3: Implement `send_message`**

Path: `/Users/dan/work/industry-checker/dingtalk_client.py`

```python
"""DingTalk client: send a signed text message to a custom robot webhook."""
import base64
import hashlib
import hmac
import time
import urllib.parse

import requests


def send_message(access_token: str, secret: str, msg: str) -> dict:
    """Send a text message to a DingTalk custom robot. Returns parsed response JSON.

    Raises RuntimeError on non-2xx HTTP or non-zero DingTalk errcode.
    """
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

    url = (
        f"https://oapi.dingtalk.com/robot/send"
        f"?access_token={access_token}&timestamp={timestamp}&sign={sign}"
    )
    body = {"msgtype": "text", "text": {"content": msg}}

    resp = requests.post(url, json=body, headers={"Content-Type": "application/json"}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"DingTalk HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"DingTalk error: {data.get('errmsg')}")
    return data
```

- [ ] **Step 4: Run tests, expect both passing**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_dingtalk_client.py -v
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add dingtalk_client.py tests/test_dingtalk_client.py && git commit -m "feat: extract send_message into dingtalk_client module"
```

---

## Task 4: Create `report.format_section`

**Files:**
- Create: `/Users/dan/work/industry-checker/report.py`
- Create: `/Users/dan/work/industry-checker/tests/test_report.py`

- [ ] **Step 1: Write failing tests**

Path: `/Users/dan/work/industry-checker/tests/test_report.py`

```python
from report import format_section


def test_format_section_with_data():
    summary = {
        "total": 14,
        "with_industry": 11,
        "distribution": [
            {"name": "Manufacturing", "count": 5, "percent": 45.45},
            {"name": "F&B", "count": 3, "percent": 27.27},
            {"name": "Retail", "count": 2, "percent": 18.18},
            {"name": "Logistics", "count": 1, "percent": 9.10},
        ],
    }
    text = format_section("2026-06-02 (yesterday)", summary)
    lines = text.splitlines()

    assert lines[0] == "=== Industry breakdown: 2026-06-02 (yesterday) ==="
    assert lines[1] == "Total contacts created: 14"
    assert lines[2] == "With industry filled:   11"
    assert lines[3] == ""
    # Industry rows: name left-padded to longest, count right-aligned width 3, percent like "45.5%"
    assert "Manufacturing" in lines[4]
    assert "5" in lines[4]
    assert "45.5%" in lines[4]
    assert "Logistics" in lines[-1]
    assert "9.1%" in lines[-1]


def test_format_section_empty():
    summary = {"total": 0, "with_industry": 0, "distribution": []}
    text = format_section("2026-06-02 (yesterday)", summary)
    assert text == (
        "=== Industry breakdown: 2026-06-02 (yesterday) ===\n"
        "(no contacts in this window)"
    )
```

- [ ] **Step 2: Run tests, expect failure**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_report.py -v
```
Expected: both tests fail at import — `ModuleNotFoundError: No module named 'report'`.

- [ ] **Step 3: Implement `format_section`**

Path: `/Users/dan/work/industry-checker/report.py`

```python
"""Format a HubSpot industry summary into a text section for DingTalk."""


def format_section(label: str, summary: dict) -> str:
    """Build one labeled industry breakdown block as plain text."""
    header = f"=== Industry breakdown: {label} ==="

    if summary["total"] == 0:
        return f"{header}\n(no contacts in this window)"

    lines = [
        header,
        f"Total contacts created: {summary['total']}",
        f"With industry filled:   {summary['with_industry']}",
        "",
    ]
    if summary["distribution"]:
        pad = max(len(row["name"]) for row in summary["distribution"])
        for row in summary["distribution"]:
            pct = f"{row['percent']:.1f}%"
            lines.append(f"  {row['name']:<{pad}}  {row['count']:>3}  {pct:>6}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests, expect both passing**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_report.py -v
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add report.py tests/test_report.py && git commit -m "feat: add report.format_section for industry breakdown text"
```

---

## Task 5: Implement `compute_windows` in `daily_report.py`

This computes the date math without doing any HTTP. We TDD it first, then layer the orchestration logic on top in Task 6.

**Files:**
- Create: `/Users/dan/work/industry-checker/daily_report.py`
- Create: `/Users/dan/work/industry-checker/tests/test_daily_report.py`

- [ ] **Step 1: Write failing tests**

Path: `/Users/dan/work/industry-checker/tests/test_daily_report.py`

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from daily_report import compute_windows

SGT = ZoneInfo("Asia/Singapore")


def _sgt_ms(y, m, d, h=0, mi=0, s=0, ms=0):
    """Return SGT-local datetime converted to epoch milliseconds."""
    dt = datetime(y, m, d, h, mi, s, ms * 1000, tzinfo=SGT)
    return int(dt.timestamp() * 1000)


def test_compute_windows_midweek():
    now_sgt = datetime(2026, 6, 3, 9, 0, tzinfo=SGT)  # Wed
    windows = compute_windows(now_sgt)

    assert len(windows) == 2
    yesterday, wtd = windows

    assert yesterday[0] == "2026-06-02 (yesterday)"
    assert yesterday[1] == _sgt_ms(2026, 6, 2, 0, 0, 0, 0)
    assert yesterday[2] == _sgt_ms(2026, 6, 2, 23, 59, 59, 999)

    assert wtd[0] == "2026-06-01 to 2026-06-02 (WTD)"
    assert wtd[1] == _sgt_ms(2026, 6, 1, 0, 0, 0, 0)
    assert wtd[2] == _sgt_ms(2026, 6, 2, 23, 59, 59, 999)


def test_compute_windows_tuesday_single_day_wtd():
    now_sgt = datetime(2026, 6, 2, 9, 0, tzinfo=SGT)  # Tue
    _, wtd = compute_windows(now_sgt)
    assert wtd[0] == "2026-06-01 (WTD)"
    assert wtd[1] == _sgt_ms(2026, 6, 1, 0, 0, 0, 0)
    assert wtd[2] == _sgt_ms(2026, 6, 1, 23, 59, 59, 999)


def test_compute_windows_monday_morning():
    now_sgt = datetime(2026, 6, 8, 9, 0, tzinfo=SGT)  # Mon
    yesterday, wtd = compute_windows(now_sgt)

    assert yesterday[0] == "2026-06-07 (yesterday)"
    assert yesterday[1] == _sgt_ms(2026, 6, 7, 0, 0, 0, 0)
    assert yesterday[2] == _sgt_ms(2026, 6, 7, 23, 59, 59, 999)

    # WTD invalid: week just started
    assert wtd[0] == "WTD"
    assert wtd[1] is None
    assert wtd[2] is None
```

- [ ] **Step 2: Run tests, expect failure**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_daily_report.py -v
```
Expected: all three tests fail at import — `ModuleNotFoundError: No module named 'daily_report'`.

- [ ] **Step 3: Implement `compute_windows`**

Path: `/Users/dan/work/industry-checker/daily_report.py`

```python
"""Daily HubSpot industry breakdown → DingTalk group.

Run: python daily_report.py

Computes yesterday + WTD (Mon → yesterday) windows in SGT, fetches HubSpot
contacts in each window, summarizes industry distribution, and posts the
combined report to a DingTalk group via signed webhook.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SGT = ZoneInfo("Asia/Singapore")


def _sgt_day_bounds_ms(d: datetime) -> tuple[int, int]:
    """Return (start_ms, end_ms) for the calendar day of `d` in SGT."""
    start = d.replace(hour=0, minute=0, second=0, microsecond=0)
    end = d.replace(hour=23, minute=59, second=59, microsecond=999000)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def compute_windows(now_sgt: datetime) -> list[tuple[str, int | None, int | None]]:
    """Return [(label, start_ms, end_ms)] for yesterday and WTD.

    WTD spans Monday-of-this-week 00:00 SGT through yesterday 23:59:59.999 SGT.
    If today is Monday, WTD is invalid and start/end are None.
    """
    today = now_sgt.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    y_start, y_end = _sgt_day_bounds_ms(yesterday)
    yesterday_window = (f"{yesterday.date().isoformat()} (yesterday)", y_start, y_end)

    monday_of_week = today - timedelta(days=today.weekday())
    if monday_of_week > yesterday:
        wtd_window = ("WTD", None, None)
    else:
        w_start, _ = _sgt_day_bounds_ms(monday_of_week)
        _, w_end = _sgt_day_bounds_ms(yesterday)
        if monday_of_week.date() == yesterday.date():
            label = f"{yesterday.date().isoformat()} (WTD)"
        else:
            label = f"{monday_of_week.date().isoformat()} to {yesterday.date().isoformat()} (WTD)"
        wtd_window = (label, w_start, w_end)

    return [yesterday_window, wtd_window]
```

- [ ] **Step 4: Run tests, expect all three passing**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_daily_report.py -v
```
Expected: `3 passed`.

- [ ] **Step 5: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add daily_report.py tests/test_daily_report.py && git commit -m "feat: add compute_windows for yesterday + WTD in SGT"
```

---

## Task 6: Wire up `daily_report.main()` orchestration

This connects compute_windows → hubspot_client → report → dingtalk_client. Single unit test verifies the end-to-end flow with mocks.

**Files:**
- Modify: `/Users/dan/work/industry-checker/daily_report.py`
- Modify: `/Users/dan/work/industry-checker/tests/test_daily_report.py`

- [ ] **Step 1: Add failing orchestration test**

Append to `/Users/dan/work/industry-checker/tests/test_daily_report.py`:

```python
from unittest.mock import patch

from daily_report import build_report_message


def test_build_report_message_full_flow(monkeypatch):
    monkeypatch.setenv("HUBSPOT_PRIVATE_APP_TOKEN", "fake")

    yesterday_contacts = [
        {"your_industry": "Manufacturing"},
        {"your_industry": "F&B"},
    ]
    wtd_contacts = [
        {"your_industry": "Manufacturing"},
        {"your_industry": "Manufacturing"},
        {"your_industry": "F&B"},
    ]

    now_sgt = datetime(2026, 6, 3, 9, 0, tzinfo=SGT)
    with patch(
        "daily_report.fetch_contacts",
        side_effect=[yesterday_contacts, wtd_contacts],
    ) as fetch:
        message = build_report_message(now_sgt)

    assert fetch.call_count == 2
    # Yesterday section appears first, then WTD section.
    assert message.index("=== Industry breakdown: 2026-06-02 (yesterday) ===") < message.index(
        "=== Industry breakdown: 2026-06-01 to 2026-06-02 (WTD) ==="
    )
    assert "Manufacturing" in message


def test_build_report_message_handles_invalid_wtd(monkeypatch):
    monkeypatch.setenv("HUBSPOT_PRIVATE_APP_TOKEN", "fake")

    now_sgt = datetime(2026, 6, 8, 9, 0, tzinfo=SGT)  # Monday
    with patch("daily_report.fetch_contacts", return_value=[]) as fetch:
        message = build_report_message(now_sgt)

    # Only the yesterday window triggers a fetch; WTD is skipped.
    assert fetch.call_count == 1
    assert "=== Industry breakdown: WTD ===" in message
    assert "(week just started — no data yet)" in message
```

- [ ] **Step 2: Run tests, expect the two new tests to fail**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest tests/test_daily_report.py -v
```
Expected: 3 prior `compute_windows` tests pass; 2 new tests fail with `ImportError: cannot import name 'build_report_message'`.

- [ ] **Step 3: Implement `build_report_message` and `main`**

Append to `/Users/dan/work/industry-checker/daily_report.py`:

```python
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from dingtalk_client import send_message
from hubspot_client import fetch_contacts, summarize_industry
from report import format_section

SCRIPT_DIR = Path(__file__).resolve().parent


def build_report_message(now_sgt: datetime) -> str:
    """Compute windows, fetch + summarize each, return joined report text."""
    sections: list[str] = []
    for label, start_ms, end_ms in compute_windows(now_sgt):
        if start_ms is None or end_ms is None:
            sections.append(
                f"=== Industry breakdown: {label} ===\n(week just started — no data yet)"
            )
            continue
        contacts = fetch_contacts(start_ms, end_ms, ["your_industry"])
        summary = summarize_industry(contacts)
        sections.append(format_section(label, summary))
    return "\n\n".join(sections)


def main() -> int:
    load_dotenv(SCRIPT_DIR / ".env")

    dingtalk_token = os.environ.get("DINGTALK_ACCESS_TOKEN")
    dingtalk_secret = os.environ.get("DINGTALK_SECRET")
    if not dingtalk_token:
        raise RuntimeError("DINGTALK_ACCESS_TOKEN is not set")
    if not dingtalk_secret:
        raise RuntimeError("DINGTALK_SECRET is not set")

    now_sgt = datetime.now(SGT)
    message = build_report_message(now_sgt)

    print(message)
    print("---", flush=True)
    send_message(dingtalk_token, dingtalk_secret, message)
    print("Posted to DingTalk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Also adjust the top imports so the file's import order is: stdlib, third-party, local. Final import block at the top of `daily_report.py`:

```python
"""Daily HubSpot industry breakdown → DingTalk group.

Run: python daily_report.py

Computes yesterday + WTD (Mon → yesterday) windows in SGT, fetches HubSpot
contacts in each window, summarizes industry distribution, and posts the
combined report to a DingTalk group via signed webhook.
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from dingtalk_client import send_message
from hubspot_client import fetch_contacts, summarize_industry
from report import format_section
```

(Remove the duplicate `import os`, `import sys`, `from pathlib import Path`, and `from dotenv import load_dotenv` that were appended in step 3.)

- [ ] **Step 4: Run all tests, expect everything passing**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest -v
```
Expected: **all green, zero failed, zero errored**. The total count should be 15 (4 summarize + 2 fetch + 2 dingtalk + 2 report + 3 compute_windows + 2 build_report_message).

- [ ] **Step 5: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add daily_report.py tests/test_daily_report.py && git commit -m "feat: wire up daily_report.main with build_report_message orchestration"
```

---

## Task 7: Refactor `check_industry.py` to use the new modules

The existing file duplicates the fetch + summarize + print logic. Replace it with thin glue that imports from `hubspot_client` and `report`. Behavior (single-window breakdown printed to stdout based on `START_DATE`/`END_DATE` constants) is preserved.

**Files:**
- Modify: `/Users/dan/work/industry-checker/check_industry.py`

- [ ] **Step 1: Read existing `check_industry.py`**

Run:
```bash
cd /Users/dan/work/industry-checker && cat check_industry.py
```
Expected: see the current 120-line file (`fetch_hubspot_contacts`, `summarize_industry`, `_date_to_ms`, `main`).

- [ ] **Step 2: Rewrite `check_industry.py`**

Replace entire file contents:

Path: `/Users/dan/work/industry-checker/check_industry.py`

```python
"""Single-window industry breakdown CLI. Edit START_DATE/END_DATE and run:

    python check_industry.py

Counts only contacts with `your_industry` filled in. Date filter is on
`createdate` (UTC) — i.e. "leads first created in HubSpot during this
period," not "leads modified during this period."
"""
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from hubspot_client import fetch_contacts, summarize_industry
from report import format_section

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

START_DATE = "2026-06-01"
END_DATE = "2026-06-03"


def _date_to_ms(date_str: str, end_of_day: bool = False) -> int:
    suffix = "T23:59:59.999000+00:00" if end_of_day else "T00:00:00+00:00"
    return int(datetime.fromisoformat(date_str + suffix).timestamp() * 1000)


def main() -> None:
    start_ms = _date_to_ms(START_DATE)
    end_ms = _date_to_ms(END_DATE, end_of_day=True)
    label = START_DATE if START_DATE == END_DATE else f"{START_DATE} to {END_DATE}"

    contacts = fetch_contacts(start_ms, end_ms, ["your_industry"])
    summary = summarize_industry(contacts)
    print(format_section(label, summary))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke-check the import path works (no real HTTP)**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/python -c "import check_industry; print('imports ok')"
```
Expected: `imports ok` printed; no traceback.

- [ ] **Step 4: Run pytest to confirm nothing else broke**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest -v
```
Expected: same all-green result as Task 6.

- [ ] **Step 5: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add check_industry.py && git commit -m "refactor: check_industry CLI uses hubspot_client + report modules"
```

---

## Task 8: Refactor `send_custom_robot_group_message.py` to use `dingtalk_client`

Preserve the existing CLI flags including `--userid`, `--at_mobiles`, `--is_at_all`. The signed-send logic moves to `dingtalk_client.send_message`, but `send_message` doesn't support @-mentions; build the richer body locally in the CLI.

**Files:**
- Modify: `/Users/dan/work/industry-checker/send_custom_robot_group_message.py`

- [ ] **Step 1: Rewrite the file**

Path: `/Users/dan/work/industry-checker/send_custom_robot_group_message.py`

```python
#!/usr/bin/env python
"""Standalone DingTalk custom robot CLI. Supports @-mentioning users/mobiles.

For the daily report cron, use daily_report.py instead — this CLI is for
ad-hoc sends.
"""
import argparse
import base64
import hashlib
import hmac
import logging
import time
import urllib.parse

import requests


def setup_logger():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(name)-8s %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]"
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def define_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--access_token", dest="access_token", required=True)
    parser.add_argument("--secret", dest="secret", required=True)
    parser.add_argument("--userid", dest="userid", help="comma-separated DingTalk user IDs to @")
    parser.add_argument("--at_mobiles", dest="at_mobiles", help="comma-separated mobiles to @")
    parser.add_argument("--is_at_all", dest="is_at_all", action="store_true")
    parser.add_argument("--msg", dest="msg", default="钉钉，让进步发生")
    return parser.parse_args()


def send_with_mentions(access_token, secret, msg, at_user_ids=None, at_mobiles=None, is_at_all=False):
    """Signed send including @-mention block. Returns parsed response JSON."""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

    url = (
        f"https://oapi.dingtalk.com/robot/send"
        f"?access_token={access_token}&timestamp={timestamp}&sign={sign}"
    )
    body = {
        "at": {
            "isAtAll": str(is_at_all).lower(),
            "atUserIds": at_user_ids or [],
            "atMobiles": at_mobiles or [],
        },
        "text": {"content": msg},
        "msgtype": "text",
    }
    resp = requests.post(url, json=body, headers={"Content-Type": "application/json"}, timeout=30)
    logging.info("DingTalk response: %s", resp.text)
    return resp.json()


def main():
    setup_logger()
    options = define_options()
    at_user_ids = [u.strip() for u in (options.userid or "").split(",") if u.strip()]
    at_mobiles = [m.strip() for m in (options.at_mobiles or "").split(",") if m.strip()]
    send_with_mentions(
        options.access_token,
        options.secret,
        options.msg,
        at_user_ids=at_user_ids,
        at_mobiles=at_mobiles,
        is_at_all=options.is_at_all,
    )


if __name__ == "__main__":
    main()
```

Note: this CLI keeps its own signed-send because `dingtalk_client.send_message` deliberately doesn't carry the @-mention payload. The duplication is intentional and minimal (≈10 lines of signing code shared). Per the spec, the daily report does not @-mention anyone so the common module stays small.

- [ ] **Step 2: Smoke-check the file parses and CLI help works**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/python send_custom_robot_group_message.py --help
```
Expected: argparse help text listing `--access_token`, `--secret`, `--userid`, `--at_mobiles`, `--is_at_all`, `--msg`.

- [ ] **Step 3: Run pytest to confirm nothing else broke**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/pytest -v
```
Expected: same all-green result as Task 7.

- [ ] **Step 4: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add send_custom_robot_group_message.py && git commit -m "refactor: clean up DingTalk CLI; keep @-mention support local"
```

---

## Task 9: Add `render.yaml` for Render cron deploy

**Files:**
- Create: `/Users/dan/work/industry-checker/render.yaml`

- [ ] **Step 1: Write `render.yaml`**

Path: `/Users/dan/work/industry-checker/render.yaml`

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

- [ ] **Step 2: Sanity-check YAML parses**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/python -c "import yaml" 2>/dev/null || .venv/bin/pip install pyyaml
.venv/bin/python -c "import yaml; print(yaml.safe_load(open('render.yaml')))"
```
Expected: a Python dict printed showing the service definition. No `YAMLError`.

(You can uninstall `pyyaml` after if you don't want it as a dep: `.venv/bin/pip uninstall -y pyyaml`. It's not used at runtime.)

- [ ] **Step 3: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add render.yaml && git commit -m "chore: add render.yaml for daily cron deploy"
```

---

## Task 10: Write `README.md` with setup + run instructions

**Files:**
- Create: `/Users/dan/work/industry-checker/README.md`

- [ ] **Step 1: Write README**

Path: `/Users/dan/work/industry-checker/README.md`

````markdown
# Industry Checker

Daily HubSpot industry breakdown → DingTalk group, run as a Render cron job.

## What it does

At 09:00 SGT each day (Render cron `0 1 * * *` UTC), posts a message to a DingTalk group with:
- Yesterday's industry breakdown.
- Week-to-date breakdown (Monday → yesterday).

Also includes two standalone CLIs:
- `check_industry.py` — print a single-window breakdown locally.
- `send_custom_robot_group_message.py` — ad-hoc DingTalk send with @-mentions.

## Setup (local dev)

1. Clone the repo.
2. Copy `.env.example` to `.env` and fill in:
   - `HUBSPOT_PRIVATE_APP_TOKEN` — from your HubSpot private app (scope `crm.objects.contacts.read`).
   - `DINGTALK_ACCESS_TOKEN` — `access_token` query param from the DingTalk robot webhook URL.
   - `DINGTALK_SECRET` — signing secret from the robot's security settings.
3. Install deps:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
4. Run tests:
   ```bash
   .venv/bin/pytest
   ```
5. Run the daily report locally (will actually post to DingTalk):
   ```bash
   .venv/bin/python daily_report.py
   ```

## Deploy to Render

1. Push the repo to GitHub.
2. Render dashboard → New → Cron Job → connect this repo. Render reads `render.yaml`.
3. In the service's Environment tab, set the three secrets above.
4. Trigger a manual run from the dashboard to confirm the DingTalk group receives the message.
5. Cron then fires daily at `0 1 * * *` UTC.

## Files

- `daily_report.py` — main entry; computes windows, fetches, formats, posts.
- `hubspot_client.py` — `fetch_contacts` (paginated HubSpot search) + `summarize_industry`.
- `dingtalk_client.py` — `send_message` (signed webhook POST).
- `report.py` — `format_section` (industry breakdown → text).
- `check_industry.py` — single-window CLI (edit `START_DATE`/`END_DATE` and run).
- `send_custom_robot_group_message.py` — ad-hoc DingTalk CLI with @-mention support.
- `render.yaml` — Render cron service config.
````

- [ ] **Step 2: Commit**

Run:
```bash
cd /Users/dan/work/industry-checker && git add README.md && git commit -m "docs: add README with setup, run, and deploy instructions"
```

---

## Task 11: Final manual smoke test

This is the only "live" step in the plan. You'll need a real HubSpot private app token and a real DingTalk robot webhook to validate the end-to-end flow.

**Files:**
- Manual: `/Users/dan/work/industry-checker/.env` (not committed)

- [ ] **Step 1: Create `.env` from template**

Run:
```bash
cd /Users/dan/work/industry-checker && cp .env.example .env
```
Then edit `.env` and replace the three placeholder values with real credentials.

- [ ] **Step 2: Run the daily report locally**

Run:
```bash
cd /Users/dan/work/industry-checker && .venv/bin/python daily_report.py
```
Expected:
1. Stdout shows the full report text (two `=== Industry breakdown: ===` sections).
2. A line `---` separator.
3. `Posted to DingTalk.`
4. The DingTalk group receives the message.
5. Exit code 0 (`echo $?` returns 0 immediately after).

- [ ] **Step 3: If output looks right, no commit needed**

The `.env` is gitignored. The actual posting is verified manually in the chat group. If you spotted any formatting bug here, fix it in `report.py` or `daily_report.py` and re-run.

---

## Self-Review

After writing the plan I checked it against the spec:

**Spec coverage:** Every spec section is implemented somewhere — Task 0 covers scaffolding, Tasks 1–2 cover `hubspot_client`, Task 3 covers `dingtalk_client`, Task 4 covers `report`, Tasks 5–6 cover `daily_report`, Tasks 7–8 cover the existing-CLI refactors, Tasks 9–10 cover Render + docs, Task 11 covers the live smoke test.

**Placeholder scan:** No "TBD", "TODO", "similar to Task N" placeholders. All code shown inline.

**Type consistency:** Function names match across tasks:
- `fetch_contacts(start_ms, end_ms, properties)` used in Tasks 2, 6, 7
- `summarize_industry(contacts)` used in Tasks 1, 6, 7
- `send_message(access_token, secret, msg)` used in Tasks 3, 6 (not in Task 8 which uses local `send_with_mentions`)
- `format_section(label, summary)` used in Tasks 4, 6, 7
- `compute_windows(now_sgt)` used in Tasks 5, 6
- `build_report_message(now_sgt)` introduced in Task 6 and only used there

Window tuple shape `(label: str, start_ms: int | None, end_ms: int | None)` consistent between Task 5 spec and Task 6 consumer.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-03-combined-hubspot-dingtalk.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
