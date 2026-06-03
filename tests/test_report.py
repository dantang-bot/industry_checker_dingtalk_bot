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
    text = format_section("2026-06-02", summary)
    lines = text.splitlines()

    assert lines[0] == "**2026-06-02**"
    assert lines[1] == ""
    assert lines[2] == "Total contacts with industry: **11**"
    assert lines[3] == ""
    assert lines[4] == "- Manufacturing: 5 (45.5%)"
    assert lines[-1] == "- Logistics: 1 (9.1%)"


def test_format_section_empty():
    summary = {"total": 0, "with_industry": 0, "distribution": []}
    text = format_section("2026-06-02", summary)
    assert text == "**2026-06-02**\n\n_(no contacts in this window)_"
