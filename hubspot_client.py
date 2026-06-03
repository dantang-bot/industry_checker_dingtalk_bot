"""HubSpot client: fetch contacts in a date window and summarize industry distribution."""
import os
from collections import Counter

import requests


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


def fetch_contacts(start_ms: int, end_ms: int, properties: list[str]) -> list[dict]:
    """Fetch HubSpot contacts created in [start_ms, end_ms] with bot_status set.

    Returns flattened list of contact properties dicts, paginated through all results.
    """
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
