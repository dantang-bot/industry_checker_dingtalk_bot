"""DingTalk client: send a markdown message to a custom robot webhook (signed or unsigned)."""
import base64
import hashlib
import hmac
import time
import urllib.parse

import requests


def send_message(access_token: str, secret: str | None, msg: str, title: str = "Industry Report") -> dict:
    """Send a markdown message to a DingTalk custom robot. Returns parsed response JSON.

    The `msg` is the markdown body (use ``` ``` for monospace blocks). `title`
    appears in chat-list previews and notifications, not in the message body.

    If secret is provided, signs the request with HMAC-SHA256. If secret is empty
    or None, posts unsigned — use this when the robot is secured by keyword match
    or IP whitelist instead of signing.

    Raises RuntimeError on non-2xx HTTP or non-zero DingTalk errcode.
    """
    if secret:
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
    else:
        url = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}"

    body = {"msgtype": "markdown", "markdown": {"title": title, "text": msg}}

    resp = requests.post(url, json=body, headers={"Content-Type": "application/json"}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"DingTalk HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"DingTalk error: {data.get('errmsg')}")
    return data
