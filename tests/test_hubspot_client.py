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
