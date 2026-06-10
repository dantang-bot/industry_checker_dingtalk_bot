"""HubSpot client: fetch contacts in a date window and summarize industry distribution."""
import os

import requests


_INDUSTRY_BUCKETS: dict[str, str] = {
    "F&B": "F&B",
    "Restaurant / Café": "F&B",
    "Bakery / Beverage / Dessert": "F&B",
    "Food Stall / Hawker": "F&B",
    "Retail": "Retail",
    "Minimart": "Retail",
    "Others": "Others",
    "Services": "Others",
    "Hair Salon": "Others",
}

_BUCKET_ORDER: tuple[str, ...] = ("F&B", "Retail", "Others")


def summarize_industry(contacts: list[dict]) -> dict:
    """Return {total, with_industry, distribution: [{name, count, percent}, ...]}.

    Raw `your_industry` values are mapped into 3 buckets — F&B, Retail, Others —
    via `_INDUSTRY_BUCKETS`. Unknown values fall through to Others. Percentages
    are over with_industry, not total. Distribution is in fixed bucket order;
    zero-count buckets are still included so the report shape is stable.
    Empty input returns an empty distribution.
    """
    with_industry = [c for c in contacts if (c.get("your_industry") or "").strip()]
    counts: dict[str, int] = {b: 0 for b in _BUCKET_ORDER}
    for c in with_industry:
        raw = (c.get("your_industry") or "").strip()
        bucket = _INDUSTRY_BUCKETS.get(raw, "Others")
        counts[bucket] += 1
    distribution = [
        {
            "name": bucket,
            "count": counts[bucket],
            "percent": counts[bucket] / len(with_industry) * 100 if with_industry else 0.0,
        }
        for bucket in _BUCKET_ORDER
    ] if with_industry else []
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
