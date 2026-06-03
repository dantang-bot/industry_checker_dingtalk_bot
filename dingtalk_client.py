"""DingTalk client: send a signed text message to a custom robot webhook."""
import base64
import hashlib
import hmac
import time
import urllib.parse

import requests


def send_message(access_token: str, secret: str, msg: str) -> dict:
    """Send a text message to a DingTalk custom robot. Returns parsed response JSON.

    Raises RuntimeError on non-2xx HTTP or non-zero DingTalk errcode.
    """
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
    body = {"msgtype": "text", "text": {"content": msg}}

    resp = requests.post(url, json=body, headers={"Content-Type": "application/json"}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"DingTalk HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"DingTalk error: {data.get('errmsg')}")
    return data
