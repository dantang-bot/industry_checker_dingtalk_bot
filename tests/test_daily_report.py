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

    assert wtd[0] == "WTD"
    assert wtd[1] is None
    assert wtd[2] is None
