"""Industry breakdown for newly-created HubSpot contacts in a date range.

Edit START_DATE / END_DATE below and run:
    python industry_checker/check_industry.py

Counts only contacts with ``your_industry`` filled in. Date filter is on
``createdate`` (UTC) -- i.e. "leads first created in HubSpot during this
period," not "leads modified during this period."
"""
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

START_DATE = "2026-06-01"
END_DATE = "2026-06-03"


def fetch_hubspot_contacts(start_ms: int, end_ms: int, properties: list[str]) -> list[dict]:
    token = os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN")
    if not token:
        raise RuntimeError("HUBSPOT_PRIVATE_APP_TOKEN is not set")

    contacts: list[dict] = []
    after: str | None = None
    while True:
        payload: dict = {
            "filterGroups": [{
                "filters": [
                    {"propertyName": "createdate", "operator": "GTE", "value": str(start_ms)},
                    {"propertyName": "createdate", "operator": "LTE", "value": str(end_ms)},
                    {"propertyName": "bot_status", "operator": "HAS_PROPERTY"},
                ],
            }],
            "properties": properties,
            "limit": 100,
            "sorts": [{"propertyName": "createdate", "direction": "ASCENDING"}],
        }
        if after:
            payload["after"] = after

        resp = requests.post(
            "https://api.hubapi.com/crm/v3/objects/contacts/search",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        for r in data.get("results", []):
            contacts.append(r.get("properties", {}))

        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break

    return contacts


def summarize_industry(contacts: list[dict]) -> dict:
    """Return {total, with_industry, distribution: [{name, count, percent}, ...]}.

    Percentages are relative to the contacts with industry filled, not total.
    Sorted descending by count.
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


def _date_to_ms(date_str: str, end_of_day: bool = False) -> int:
    suffix = "T23:59:59.999000+00:00" if end_of_day else "T00:00:00+00:00"
    return int(datetime.fromisoformat(date_str + suffix).timestamp() * 1000)


def main() -> None:
    start_ms = _date_to_ms(START_DATE)
    end_ms = _date_to_ms(END_DATE, end_of_day=True)
    label = START_DATE if START_DATE == END_DATE else f"{START_DATE} to {END_DATE}"

    contacts = fetch_hubspot_contacts(start_ms, end_ms, ["your_industry"])
    summary = summarize_industry(contacts)

    print(f"=== Industry breakdown: {label} ===")
    print(f"Total contacts created: {summary['total']}")
    print(f"With industry filled:   {summary['with_industry']}")
    print()

    if not summary["distribution"]:
        return

    pad = max(len(row["name"]) for row in summary["distribution"])
    for row in summary["distribution"]:
        pct = f"{row['percent']:.1f}%"
        print(f"  {row['name']:<{pad}}  {row['count']:>3}  {pct:>6}")


if __name__ == "__main__":
    main()
