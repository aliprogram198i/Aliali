import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from aliali.api.app import create_app
from aliali.config import Settings


BOT_TOKEN = "123456:test-token"


def _init_data() -> str:
    values = {
        "auth_date": str(int(time.time())),
        "query_id": "AAEAA",
        "user": json.dumps({"id": 42, "first_name": "Ali"}, separators=(",", ":")),
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


def test_network_target_validation_requires_telegram_auth() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post(
        "/api/v1/network/operate",
        json={
            "init_data": "auth_date=1&hash=invalid",
            "module_key": "network.asset_discovery",
            "operation": "validate",
            "ip": "192.168.1.10",
        },
    )
    assert response.status_code == 401


def test_network_ip_target_is_validated() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post(
        "/api/v1/network/operate",
        json={
            "init_data": _init_data(),
            "module_key": "network.asset_discovery",
            "operation": "validate",
            "ip": "192.168.1.10",
        },
    )
    assert response.status_code == 200
    assert response.json()["target"] == {"type": "ip", "value": "192.168.1.10"}


def test_network_mac_target_is_normalized() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post(
        "/api/v1/network/operate",
        json={
            "init_data": _init_data(),
            "module_key": "network.asset_discovery",
            "operation": "validate",
            "mac": "aa-bb-cc-dd-ee-ff",
        },
    )
    assert response.status_code == 200
    assert response.json()["target"] == {
        "type": "mac",
        "value": "AA:BB:CC:DD:EE:FF",
    }


def test_network_module_rejects_wrong_target_type() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post(
        "/api/v1/network/operate",
        json={
            "init_data": _init_data(),
            "module_key": "network.exposure",
            "operation": "validate",
            "mac": "AA:BB:CC:DD:EE:FF",
        },
    )
    assert response.status_code == 422


def test_connectivity_requires_ip_and_port() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    response = client.post(
        "/api/v1/network/operate",
        json={
            "init_data": _init_data(),
            "module_key": "network.exposure",
            "operation": "connectivity",
            "ip": "127.0.0.1",
        },
    )
    assert response.status_code == 422
