# Industry Bucketing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate raw `your_industry` HubSpot values into 3 buckets — **F&B**, **Retail**, **Others** — inside `summarize_industry`, so reports (both `check_industry.py` and `daily_report.py`) always show those 3 categories.

**Architecture:** Add a static mapping `_INDUSTRY_BUCKETS` in `hubspot_client.py` from raw industry strings to bucket names. `summarize_industry` applies the mapping to each contact's `your_industry` before counting. Unknown / unmapped values fall through to **Others**. The distribution is always returned in a fixed order: F&B, Retail, Others.

**Tech Stack:** Python 3.11, pytest.

**Bucket mapping (decided):**

| Raw value                       | Bucket  |
|---------------------------------|---------|
| `F&B`                           | F&B     |
| `Restaurant / Café`             | F&B     |
| `Bakery / Beverage / Dessert`   | F&B     |
| `Food Stall / Hawker`           | F&B     |
| `Retail`                        | Retail  |
| `Minimart`                      | Retail  |
| `Others`                        | Others  |
| `Services`                      | Others  |
| `Hair Salon`                    | Others  |
| _anything else (unknown)_       | Others  |

Matching is case-sensitive on the trimmed raw string (existing code already strips whitespace). The output distribution always lists the three buckets in the fixed order **F&B, Retail, Others**, even when a bucket has zero contacts (`count: 0`, `percent: 0`). This keeps the DingTalk report shape stable.

---

## File Structure

- **Modify** `hubspot_client.py` — add `_INDUSTRY_BUCKETS` dict and `_BUCKET_ORDER` list; rewrite `summarize_industry` to bucket before counting and emit fixed-order distribution.
- **Modify** `tests/test_hubspot_client.py` — update existing `summarize_industry` tests for the new shape; add new tests for bucketing rules, unknown-fallback, and fixed ordering.
- **Modify** `tests/test_daily_report.py` — the existing `test_build_report_message_full_flow` uses raw `"Manufacturing"`, which is now an unknown → Others; update assertion accordingly.

`report.py` (the markdown formatter) does **not** change: it just renders whatever `distribution` contains. `check_industry.py` and `daily_report.py` do not change either — they call `summarize_industry` and pass the result to `format_section`.

---

## Task 1: Add bucket mapping constants and rewrite `summarize_industry`

**Files:**
- Modify: `hubspot_client.py` (lines 8-27)
- Test: `tests/test_hubspot_client.py`

- [ ] **Step 1: Update existing `test_summarize_industry_basic` to reflect the new bucketed output**

Replace the existing `test_summarize_industry_basic` in `tests/test_hubspot_client.py` (lines 7-19) with this:

```python
def test_summarize_industry_basic_buckets():
    contacts = [
        {"your_industry": "F&B"},
        {"your_industry": "Restaurant / Café"},
        {"your_industry": "Retail"},
    ]
    result = summarize_industry(contacts)
    assert result["total"] == 3
    assert result["with_industry"] == 3
    assert result["distribution"] == [
        {"name": "F&B", "count": 2, "percent": pytest.approx(66.666, rel=1e-3)},
        {"name": "Retail", "count": 1, "percent": pytest.approx(33.333, rel=1e-3)},
        {"name": "Others", "count": 0, "percent": 0},
    ]
```

- [ ] **Step 2: Update `test_summarize_industry_strips_whitespace`**

Replace the existing test (lines 22-31) with:

```python
def test_summarize_industry_strips_whitespace():
    contacts = [
        {"your_industry": "  F&B  "},
        {"your_industry": "F&B"},
    ]
    result = summarize_industry(contacts)
    assert result["with_industry"] == 2
    assert result["distribution"] == [
        {"name": "F&B", "count": 2, "percent": 100.0},
        {"name": "Retail", "count": 0, "percent": 0},
        {"name": "Others", "count": 0, "percent": 0},
    ]
```

- [ ] **Step 3: Update `test_summarize_industry_excludes_blank`**

Replace lines 34-46 with:

```python
def test_summarize_industry_excludes_blank():
    contacts = [
        {"your_industry": "F&B"},
        {"your_industry": ""},
        {"your_industry": None},
        {},
    ]
    result = summarize_industry(contacts)
    assert result["total"] == 4
    assert result["with_industry"] == 1
    assert result["distribution"] == [
        {"name": "F&B", "count": 1, "percent": 100.0},
        {"name": "Retail", "count": 0, "percent": 0},
        {"name": "Others", "count": 0, "percent": 0},
    ]
```

- [ ] **Step 4: Update `test_summarize_industry_empty`**

Replace lines 49-51 with:

```python
def test_summarize_industry_empty():
    result = summarize_industry([])
    assert result == {"total": 0, "with_industry": 0, "distribution": []}
```

(No change in behavior — empty contact list still returns an empty distribution. The fixed-order three-row distribution only applies when there is at least one contact.)

- [ ] **Step 5: Add new test for full F&B bucket coverage**

Append to `tests/test_hubspot_client.py`:

```python
def test_summarize_industry_buckets_fnb_values():
    contacts = [
        {"your_industry": "F&B"},
        {"your_industry": "Restaurant / Café"},
        {"your_industry": "Bakery / Beverage / Dessert"},
        {"your_industry": "Food Stall / Hawker"},
    ]
    result = summarize_industry(contacts)
    fnb_row = next(r for r in result["distribution"] if r["name"] == "F&B")
    assert fnb_row["count"] == 4
    assert fnb_row["percent"] == 100.0
```

- [ ] **Step 6: Add new test for full Retail bucket coverage**

Append to `tests/test_hubspot_client.py`:

```python
def test_summarize_industry_buckets_retail_values():
    contacts = [
        {"your_industry": "Retail"},
        {"your_industry": "Minimart"},
    ]
    result = summarize_industry(contacts)
    retail_row = next(r for r in result["distribution"] if r["name"] == "Retail")
    assert retail_row["count"] == 2
    assert retail_row["percent"] == 100.0
```

- [ ] **Step 7: Add new test for full Others bucket coverage**

Append to `tests/test_hubspot_client.py`:

```python
def test_summarize_industry_buckets_others_values():
    contacts = [
        {"your_industry": "Others"},
        {"your_industry": "Services"},
        {"your_industry": "Hair Salon"},
    ]
    result = summarize_industry(contacts)
    others_row = next(r for r in result["distribution"] if r["name"] == "Others")
    assert others_row["count"] == 3
    assert others_row["percent"] == 100.0
```

- [ ] **Step 8: Add new test for unknown-value fallback to Others**

Append to `tests/test_hubspot_client.py`:

```python
def test_summarize_industry_unknown_values_fall_into_others():
    contacts = [
        {"your_industry": "Manufacturing"},
        {"your_industry": "Logistics"},
        {"your_industry": "F&B"},
    ]
    result = summarize_industry(contacts)
    assert result["distribution"] == [
        {"name": "F&B", "count": 1, "percent": pytest.approx(33.333, rel=1e-3)},
        {"name": "Retail", "count": 0, "percent": 0},
        {"name": "Others", "count": 2, "percent": pytest.approx(66.666, rel=1e-3)},
    ]
```

- [ ] **Step 9: Add new test confirming fixed F&B → Retail → Others ordering**

Append to `tests/test_hubspot_client.py`:

```python
def test_summarize_industry_distribution_order_is_fixed():
    # Even when Others dominates, the order is F&B, Retail, Others.
    contacts = [
        {"your_industry": "Services"},
        {"your_industry": "Services"},
        {"your_industry": "Services"},
        {"your_industry": "F&B"},
    ]
    result = summarize_industry(contacts)
    names = [row["name"] for row in result["distribution"]]
    assert names == ["F&B", "Retail", "Others"]
```

- [ ] **Step 10: Run the updated test file and confirm the new/modified tests fail**

Run: `pytest tests/test_hubspot_client.py -v`

Expected: The four updated tests (`test_summarize_industry_basic_buckets`, `..._strips_whitespace`, `..._excludes_blank`, `..._empty` should still pass) — but `..._basic_buckets`, `..._strips_whitespace`, `..._excludes_blank`, and the five new bucket tests should FAIL because the current `summarize_industry` does not bucket and does not emit fixed-order zero rows. (`..._empty` and the `fetch_contacts` tests should still pass unchanged.)

- [ ] **Step 11: Rewrite `summarize_industry` in `hubspot_client.py`**

Replace the existing `summarize_industry` function (lines 8-27 of `hubspot_client.py`) with:

```python
_INDUSTRY_BUCKETS: dict[str, str] = {
    "F&B": "F&B",
    "Restaurant / Café": "F&B",
    "Bakery / Beverage / Dessert": "F&B",
    "Food Stall / Hawker": "F&B",
    "Retail": "Retail",
    "Minimart": "Retail",
    "Others": "Others",
    "Services": "Others",
    "Hair Salon": "Others",
}

_BUCKET_ORDER: tuple[str, ...] = ("F&B", "Retail", "Others")


def summarize_industry(contacts: list[dict]) -> dict:
    """Return {total, with_industry, distribution: [{name, count, percent}, ...]}.

    Raw `your_industry` values are mapped into 3 buckets — F&B, Retail, Others —
    via `_INDUSTRY_BUCKETS`. Unknown values fall through to Others. Percentages
    are over with_industry, not total. Distribution is in fixed bucket order;
    zero-count buckets are still included so the report shape is stable.
    Empty input returns an empty distribution.
    """
    with_industry = [c for c in contacts if (c.get("your_industry") or "").strip()]
    counts: dict[str, int] = {b: 0 for b in _BUCKET_ORDER}
    for c in with_industry:
        raw = (c.get("your_industry") or "").strip()
        bucket = _INDUSTRY_BUCKETS.get(raw, "Others")
        counts[bucket] += 1
    distribution = [
        {
            "name": bucket,
            "count": counts[bucket],
            "percent": counts[bucket] / len(with_industry) * 100 if with_industry else 0,
        }
        for bucket in _BUCKET_ORDER
    ] if with_industry else []
    return {
        "total": len(contacts),
        "with_industry": len(with_industry),
        "distribution": distribution,
    }
```

Leave the `Counter` import line (`from collections import Counter`) — it is no longer used after this change, so remove it as well. The final imports section at the top of `hubspot_client.py` should be:

```python
"""HubSpot client: fetch contacts in a date window and summarize industry distribution."""
import os

import requests
```

- [ ] **Step 12: Run the hubspot_client tests and confirm they all pass**

Run: `pytest tests/test_hubspot_client.py -v`

Expected: all tests PASS — the four updated tests and the five new bucket tests, plus the existing `fetch_contacts` tests unchanged.

- [ ] **Step 13: Commit**

```bash
git add hubspot_client.py tests/test_hubspot_client.py
git commit -m "feat: bucket industry into F&B, Retail, Others"
```

---

## Task 2: Fix the `daily_report` integration test that asserted raw `Manufacturing`

**Files:**
- Modify: `tests/test_daily_report.py` (the `test_build_report_message_full_flow` test, around lines 60-85)

The current test puts `{"your_industry": "Manufacturing"}` into the mocked contacts and asserts `"Manufacturing" in message`. After Task 1, `Manufacturing` is mapped into the **Others** bucket, so the rendered message will no longer contain the string `"Manufacturing"`.

- [ ] **Step 1: Read the existing test to confirm the exact assertions**

Run: `pytest tests/test_daily_report.py::test_build_report_message_full_flow -v`

Expected: FAIL — the assertion `"Manufacturing" in message` no longer holds because the report renders buckets, not raw industries.

- [ ] **Step 2: Update the assertion in `tests/test_daily_report.py`**

In `test_build_report_message_full_flow`, locate the final assertion:

```python
    assert "Manufacturing" in message
```

Replace it with assertions that match the bucketed output. The yesterday window has 1 Manufacturing + 1 F&B (so Others=1, F&B=1, Retail=0); WTD has 2 Manufacturing + 1 F&B (so Others=2, F&B=1, Retail=0). Use:

```python
    assert "F&B" in message
    assert "Others" in message
    assert "Manufacturing" not in message
```

(Keep the surrounding test code — env var, contacts setup, `compute_windows` SGT date, the `patch("daily_report.fetch_contacts", ...)` block, and the existing `"**2026-06-02**"` / `"**WTD**"` ordering assertion — untouched.)

- [ ] **Step 3: Run the updated test to confirm it passes**

Run: `pytest tests/test_daily_report.py -v`

Expected: all tests PASS, including `test_build_report_message_full_flow`.

- [ ] **Step 4: Run the full test suite to confirm nothing else regressed**

Run: `pytest -v`

Expected: every test passes (`test_hubspot_client.py`, `test_daily_report.py`, `test_dingtalk_client.py`, `test_report.py`).

- [ ] **Step 5: Commit**

```bash
git add tests/test_daily_report.py
git commit -m "test: update daily_report integration test for bucketed industries"
```

---

## Task 3: Manual smoke-check of `check_industry.py` output format

**Files:**
- (No code changes; this is a smoke verification step.)

- [ ] **Step 1: Construct a quick in-process check that does not require HubSpot credentials**

Run this one-liner from the project root to confirm the rendered DingTalk markdown looks right with the new buckets:

```bash
python -c "
from hubspot_client import summarize_industry
from report import format_section

contacts = [
    {'your_industry': 'F&B'},
    {'your_industry': 'F&B'},
    {'your_industry': 'Restaurant / Café'},
    {'your_industry': 'Retail'},
    {'your_industry': 'Minimart'},
    {'your_industry': 'Services'},
    {'your_industry': 'Hair Salon'},
    {'your_industry': 'Manufacturing'},
]
print(format_section('smoke-test', summarize_industry(contacts)))
"
```

Expected output (exact):

```
**smoke-test**

Total contacts with industry: **8**

- F&B: 3 (37.5%)
- Retail: 2 (25%)
- Others: 3 (37.5%)
```

If the order or counts differ, debug Task 1's mapping before continuing.

- [ ] **Step 2: No commit needed for this task** (it is verification only)

---

## Self-Review

**Spec coverage:**
- F&B / Retail / Others as the only 3 buckets — Task 1, `_BUCKET_ORDER`.
- Minimart → Retail — Task 1, `_INDUSTRY_BUCKETS["Minimart"] = "Retail"`.
- Services and Hair Salon → Others — Task 1, both mapped explicitly.
- Restaurant / Café, Bakery / Beverage / Dessert, Food Stall / Hawker → F&B — Task 1, all mapped.
- Location: inside `summarize_industry` — Task 1.

**Placeholder scan:** None — every code block is concrete; every test case has body + assertions; every command has expected output.

**Type consistency:** `_INDUSTRY_BUCKETS` (dict[str, str]), `_BUCKET_ORDER` (tuple[str, ...]), `summarize_industry` signature unchanged (`list[dict] -> dict`), return shape unchanged at the top level (`total`, `with_industry`, `distribution`), each distribution row unchanged (`name`, `count`, `percent`).
