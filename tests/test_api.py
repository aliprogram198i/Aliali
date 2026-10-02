import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from aliali.api.app import create_app
from aliali.config import Settings

BOT_TOKEN = "123456:test-token"


def _init_data(user: dict[str, object]) -> str:
    values = {
        "auth_date": str(int(time.time())),
        "query_id": "AAEAA",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(values.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)


def test_lookup_requires_valid_telegram_init_data() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post(
        "/api/v1/lookup",
        json={"init_data": "auth_date=1&hash=invalid", "target": "+33142345678"},
    )
    assert response.status_code == 401


def test_lookup_returns_phone_metadata_for_authenticated_user() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post(
        "/api/v1/lookup",
        json={"init_data": _init_data({"id": 42, "first_name": "Ali"}), "target": "+33142345678"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "phone"
    assert payload["valid"] is True
    assert payload["country_code"] == 33
    assert payload["e164"] == "+33142345678"
