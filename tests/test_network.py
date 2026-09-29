import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from aliali.api import lookup
from aliali.api.app import create_app
from aliali.config import Settings

BOT_TOKEN = "123456:test-token"


def _init_data() -> str:
    values = {
        "auth_date": str(int(time.time())),
        "query_id": "AAEAA",
        "user": json.dumps({"id": 42, "first_name": "Ali"}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_lookup_requires_telegram_auth() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post("/api/v1/lookup", json={"init_data": "bad", "target": "8.8.8.8"})
    assert response.status_code == 401


def test_private_ip_is_not_looked_up_online(monkeypatch) -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    monkeypatch.setattr(lookup, "_fetch_json", lambda _: (_ for _ in ()).throw(AssertionError()))
    response = client.post("/api/v1/lookup", json={"init_data": _init_data(), "target": "192.168.1.1"})
    assert response.status_code == 200
    assert response.json()["name"] == "عنوان IP خاص/محلي"


def test_public_ip_returns_network_name(monkeypatch) -> None:
    monkeypatch.setattr(lookup, "_fetch_json", lambda _: {
        "success": True, "city": "Mountain View", "region": "California", "country": "United States",
        "connection": {"org": "Google LLC", "isp": "Google LLC", "asn": 15169, "domain": "google.com"},
    })
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post("/api/v1/lookup", json={"init_data": _init_data(), "target": "8.8.8.8"})
    assert response.status_code == 200
    assert response.json()["name"] == "Google LLC"
    assert response.json()["asn"] == 15169


def test_mac_returns_vendor(monkeypatch) -> None:
    monkeypatch.setattr(lookup, "_fetch_text", lambda _: "Example Vendor")
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post("/api/v1/lookup", json={"init_data": _init_data(), "target": "aa-bb-cc-dd-ee-ff"})
    assert response.status_code == 200
    assert response.json()["name"] == "Example Vendor"
    assert response.json()["target"] == "AA:BB:CC:DD:EE:FF"


def test_invalid_target_is_rejected() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post("/api/v1/lookup", json={"init_data": _init_data(), "target": "not-an-ip-or-mac"})
    assert response.status_code == 422
