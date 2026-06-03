# Industry Checker

Daily HubSpot industry breakdown → DingTalk group, run as a Render cron job.

## What it does

At 09:00 SGT each day (Render cron `0 1 * * *` UTC), posts a message to a DingTalk group with:
- Yesterday's industry breakdown.
- Week-to-date breakdown (Monday → yesterday).

Also includes two standalone CLIs:
- `check_industry.py` — print a single-window breakdown locally.
- `send_custom_robot_group_message.py` — ad-hoc DingTalk send with @-mentions.

## Setup (local dev)

1. Clone the repo.
2. Copy `.env.example` to `.env` and fill in:
   - `HUBSPOT_PRIVATE_APP_TOKEN` — from your HubSpot private app (scope `crm.objects.contacts.read`).
   - `DINGTALK_ACCESS_TOKEN` — `access_token` query param from the DingTalk robot webhook URL.
   - `DINGTALK_SECRET` — signing secret from the robot's security settings.
3. Install deps:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
4. Run tests:
   ```bash
   .venv/bin/pytest
   ```
5. Run the daily report locally (will actually post to DingTalk):
   ```bash
   .venv/bin/python daily_report.py
   ```

## Deploy to Render

1. Push the repo to GitHub.
2. Render dashboard → New → Cron Job → connect this repo. Render reads `render.yaml`.
3. In the service's Environment tab, set the three secrets above.
4. Trigger a manual run from the dashboard to confirm the DingTalk group receives the message.
5. Cron then fires daily at `0 1 * * *` UTC.

## Files

- `daily_report.py` — main entry; computes windows, fetches, formats, posts.
- `hubspot_client.py` — `fetch_contacts` (paginated HubSpot search) + `summarize_industry`.
- `dingtalk_client.py` — `send_message` (signed webhook POST).
- `report.py` — `format_section` (industry breakdown → text).
- `check_industry.py` — single-window CLI (edit `START_DATE`/`END_DATE` and run).
- `send_custom_robot_group_message.py` — ad-hoc DingTalk CLI with @-mention support.
- `render.yaml` — Render cron service config.
# industry_checker_dingtalk_bot
