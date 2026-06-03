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
