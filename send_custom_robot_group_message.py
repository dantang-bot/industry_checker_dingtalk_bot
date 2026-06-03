#!/usr/bin/env python
"""Standalone DingTalk custom robot CLI. Supports @-mentioning users/mobiles.

For the daily report cron, use daily_report.py instead — this CLI is for
ad-hoc sends.
"""
import argparse
import base64
import hashlib
import hmac
import logging
import time
import urllib.parse

import requests


def setup_logger():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(name)-8s %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]"
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def define_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--access_token", dest="access_token", required=True)
    parser.add_argument("--secret", dest="secret", required=True)
    parser.add_argument("--userid", dest="userid", help="comma-separated DingTalk user IDs to @")
    parser.add_argument("--at_mobiles", dest="at_mobiles", help="comma-separated mobiles to @")
    parser.add_argument("--is_at_all", dest="is_at_all", action="store_true")
    parser.add_argument("--msg", dest="msg", default="钉钉，让进步发生")
    return parser.parse_args()


def send_with_mentions(access_token, secret, msg, at_user_ids=None, at_mobiles=None, is_at_all=False):
    """Signed send including @-mention block. Returns parsed response JSON."""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

    url = (
        f"https://oapi.dingtalk.com/robot/send"
        f"?access_token={access_token}&timestamp={timestamp}&sign={sign}"
    )
    body = {
        "at": {
            "isAtAll": str(is_at_all).lower(),
            "atUserIds": at_user_ids or [],
            "atMobiles": at_mobiles or [],
        },
        "text": {"content": msg},
        "msgtype": "text",
    }
    resp = requests.post(url, json=body, headers={"Content-Type": "application/json"}, timeout=30)
    logging.info("DingTalk response: %s", resp.text)
    return resp.json()


def main():
    setup_logger()
    options = define_options()
    at_user_ids = [u.strip() for u in (options.userid or "").split(",") if u.strip()]
    at_mobiles = [m.strip() for m in (options.at_mobiles or "").split(",") if m.strip()]
    send_with_mentions(
        options.access_token,
        options.secret,
        options.msg,
        at_user_ids=at_user_ids,
        at_mobiles=at_mobiles,
        is_at_all=options.is_at_all,
    )


if __name__ == "__main__":
    main()
