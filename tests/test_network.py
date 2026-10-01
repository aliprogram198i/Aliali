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
    assert response.json()["scope"] == "Private/Local"


def test_public_ip_returns_network_details(monkeypatch) -> None:
    monkeypatch.setattr(lookup, "_fetch_json", lambda _: {
        "success": True, "type": "IPv4", "city": "Mountain View", "region": "California",
        "country": "United States", "country_code": "US", "continent": "North America",
        "latitude": 37.386, "longitude": -122.0838, "is_eu": False,
        "connection": {"org": "Google LLC", "isp": "Google LLC", "asn": 15169, "domain": "google.com"},
        "timezone": {"id": "America/Los_Angeles", "utc": "-08:00"},
    })
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post("/api/v1/lookup", json={"init_data": _init_data(), "target": "8.8.8.8"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Google LLC"
    assert payload["asn"] == 15169
    assert payload["country_code"] == "US"
    assert payload["latitude"] == 37.386
    assert payload["timezone"] == "America/Los_Angeles"
    assert payload["source"] == "ipwho.is"


def test_mac_returns_vendor_and_oui(monkeypatch) -> None:
    monkeypatch.setattr(lookup, "_fetch_text", lambda _: "Example Vendor")
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post("/api/v1/lookup", json={"init_data": _init_data(), "target": "aa-bb-cc-dd-ee-ff"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Example Vendor"
    assert payload["target"] == "AA:BB:CC:DD:EE:FF"
    assert payload["oui"] == "AA:BB:CC"
    assert payload["assignment"] == "Locally administered"


def test_invalid_target_is_rejected() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post("/api/v1/lookup", json={"init_data": _init_data(), "target": "not-an-ip-or-mac"})
    assert response.status_code == 422
