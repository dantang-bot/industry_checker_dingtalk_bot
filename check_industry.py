"""Single-window industry breakdown CLI. Edit START_DATE/END_DATE and run:

    python check_industry.py

Counts only contacts with `your_industry` filled in. Date filter is on
`createdate` (UTC) — i.e. "leads first created in HubSpot during this
period," not "leads modified during this period."
"""
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from hubspot_client import fetch_contacts, summarize_industry
from report import format_section

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

START_DATE = "2026-06-01"
END_DATE = "2026-06-03"


def _date_to_ms(date_str: str, end_of_day: bool = False) -> int:
    suffix = "T23:59:59.999000+00:00" if end_of_day else "T00:00:00+00:00"
    return int(datetime.fromisoformat(date_str + suffix).timestamp() * 1000)


def main() -> None:
    start_ms = _date_to_ms(START_DATE)
    end_ms = _date_to_ms(END_DATE, end_of_day=True)
    label = START_DATE if START_DATE == END_DATE else f"{START_DATE} to {END_DATE}"

    contacts = fetch_contacts(start_ms, end_ms, ["your_industry"])
    summary = summarize_industry(contacts)
    print(format_section(label, summary))


if __name__ == "__main__":
    main()
