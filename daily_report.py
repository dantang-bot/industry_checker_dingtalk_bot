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

SGT = ZoneInfo("Asia/Singapore")
SCRIPT_DIR = Path(__file__).resolve().parent


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


def build_report_message(now_sgt: datetime) -> str:
    """Compute windows, fetch + summarize each, return joined report text."""
    sections: list[str] = []
    windows = compute_windows(now_sgt)
    first_bounds = (windows[0][1], windows[0][2]) if windows else None
    for i, (label, start_ms, end_ms) in enumerate(windows):
        if i > 0 and (start_ms, end_ms) == first_bounds:
            continue
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
    hubspot_token = os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN")
    if not dingtalk_token:
        raise RuntimeError("DINGTALK_ACCESS_TOKEN is not set")
    if not dingtalk_secret:
        raise RuntimeError("DINGTALK_SECRET is not set")
    if not hubspot_token:
        raise RuntimeError("HUBSPOT_PRIVATE_APP_TOKEN is not set")

    now_sgt = datetime.now(SGT)
    message = build_report_message(now_sgt)

    print(message)
    print("---", flush=True)
    send_message(dingtalk_token, dingtalk_secret, message)
    print("Posted to DingTalk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
