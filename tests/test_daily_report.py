import pytest
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

    assert yesterday[0] == "2026-06-02"
    assert yesterday[1] == _sgt_ms(2026, 6, 2, 0, 0, 0, 0)
    assert yesterday[2] == _sgt_ms(2026, 6, 2, 23, 59, 59, 999)

    assert wtd[0] == "WTD"
    assert wtd[1] == _sgt_ms(2026, 6, 1, 0, 0, 0, 0)
    assert wtd[2] == _sgt_ms(2026, 6, 2, 23, 59, 59, 999)


def test_compute_windows_tuesday_single_day_wtd():
    now_sgt = datetime(2026, 6, 2, 9, 0, tzinfo=SGT)  # Tue
    _, wtd = compute_windows(now_sgt)
    assert wtd[0] == "WTD"
    assert wtd[1] == _sgt_ms(2026, 6, 1, 0, 0, 0, 0)
    assert wtd[2] == _sgt_ms(2026, 6, 1, 23, 59, 59, 999)


def test_compute_windows_monday_morning():
    now_sgt = datetime(2026, 6, 8, 9, 0, tzinfo=SGT)  # Mon
    yesterday, wtd = compute_windows(now_sgt)

    assert yesterday[0] == "2026-06-07"
    assert yesterday[1] == _sgt_ms(2026, 6, 7, 0, 0, 0, 0)
    assert yesterday[2] == _sgt_ms(2026, 6, 7, 23, 59, 59, 999)

    assert wtd[0] == "WTD"
    assert wtd[1] is None
    assert wtd[2] is None


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
    assert message.index("**2026-06-02**") < message.index("**WTD**")
    assert "Manufacturing" in message


def test_build_report_message_handles_invalid_wtd(monkeypatch):
    monkeypatch.setenv("HUBSPOT_PRIVATE_APP_TOKEN", "fake")

    now_sgt = datetime(2026, 6, 8, 9, 0, tzinfo=SGT)  # Monday
    with patch("daily_report.fetch_contacts", return_value=[]) as fetch:
        message = build_report_message(now_sgt)

    assert fetch.call_count == 1
    assert "**WTD**" in message
    assert "(week just started — no data yet)" in message


def test_build_report_message_skips_wtd_when_same_as_yesterday(monkeypatch):
    """On Tuesdays, WTD window equals yesterday window — skip the duplicate section."""
    monkeypatch.setenv("HUBSPOT_PRIVATE_APP_TOKEN", "fake")

    monday_contacts = [
        {"your_industry": "Manufacturing"},
        {"your_industry": "F&B"},
    ]

    now_sgt = datetime(2026, 6, 2, 9, 0, tzinfo=SGT)  # Tuesday
    with patch("daily_report.fetch_contacts", return_value=monday_contacts) as fetch:
        message = build_report_message(now_sgt)

    assert fetch.call_count == 1
    assert "**2026-06-01**" in message
    assert "WTD" not in message


def test_main_requires_hubspot_token(monkeypatch):
    monkeypatch.setenv("DINGTALK_ACCESS_TOKEN", "x")
    monkeypatch.setenv("DINGTALK_SECRET", "y")
    monkeypatch.delenv("HUBSPOT_PRIVATE_APP_TOKEN", raising=False)

    from daily_report import main
    with patch("daily_report.load_dotenv"):
        with pytest.raises(RuntimeError, match="HUBSPOT_PRIVATE_APP_TOKEN"):
            main()
