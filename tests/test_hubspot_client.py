import pytest
from unittest.mock import MagicMock, patch

from hubspot_client import summarize_industry, fetch_contacts


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
