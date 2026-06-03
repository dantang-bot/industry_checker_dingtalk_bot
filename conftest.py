import pytest


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for var in ("HUBSPOT_PRIVATE_APP_TOKEN", "DINGTALK_ACCESS_TOKEN", "DINGTALK_SECRET"):
        monkeypatch.delenv(var, raising=False)
