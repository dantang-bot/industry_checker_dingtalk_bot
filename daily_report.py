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
