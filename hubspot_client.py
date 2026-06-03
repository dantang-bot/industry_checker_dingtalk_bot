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
