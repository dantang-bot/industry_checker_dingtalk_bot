from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from dingtalk_client import send_message


def test_send_message_signs_request():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}

    with patch("dingtalk_client.requests.post", return_value=mock_resp) as post:
        send_message("token-abc", "SECsecret", "hello group")

    assert post.call_count == 1
    call = post.call_args

    url = call.args[0]
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert params["access_token"] == ["token-abc"]
    assert "timestamp" in params and params["timestamp"][0].isdigit()
    assert "sign" in params and len(params["sign"][0]) > 0

    body = call.kwargs["json"]
    assert body["msgtype"] == "text"
    assert body["text"] == {"content": "hello group"}


def test_send_message_unsigned_when_no_secret():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}

    with patch("dingtalk_client.requests.post", return_value=mock_resp) as post:
        send_message("token-abc", None, "hello")

    url = post.call_args.args[0]
    params = parse_qs(urlparse(url).query)
    assert params["access_token"] == ["token-abc"]
    assert "timestamp" not in params
    assert "sign" not in params


def test_send_message_raises_on_errcode():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"errcode": 310000, "errmsg": "keywords not in content"}

    with patch("dingtalk_client.requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="keywords not in content"):
            send_message("token-abc", "SECsecret", "bad message")
