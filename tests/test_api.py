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
    assert payload["evidence"]["scope"] == "public numbering-plan metadata"
    assert payload["evidence"]["metadata_version"]


def test_lookup_rate_limits_authenticated_user() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    init_data = _init_data({"id": 99, "first_name": "Rate"})
    responses = [
        client.post(
            "/api/v1/lookup",
            json={"init_data": init_data, "target": "+33142345678"},
        )
        for _ in range(21)
    ]
    assert responses[-1].status_code == 429
    assert responses[-1].headers["retry-after"] == "60"


def test_ai_analysis_uses_lookup_snapshot_without_target() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    init_data = _init_data({"id": 43, "first_name": "Snapshot"})
    lookup = client.post(
        "/api/v1/lookup",
        json={"init_data": init_data, "target": "+33142345678"},
    )
    assert lookup.status_code == 200
    analysis_id = lookup.json()["analysis_id"]
    response = client.post(
        "/api/v1/ai-analysis",
        json={"init_data": init_data, "analysis_id": analysis_id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"] == analysis_id
    assert payload["verification"]["verified"] is True


def test_ai_analysis_has_independent_rate_limit() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    init_data = _init_data({"id": 45, "first_name": "AIRate"})
    lookup = client.post(
        "/api/v1/lookup",
        json={"init_data": init_data, "target": "+33142345678"},
    )
    assert lookup.status_code == 200
    analysis_id = lookup.json()["analysis_id"]
    responses = [
        client.post(
            "/api/v1/ai-analysis",
            json={"init_data": init_data, "analysis_id": analysis_id},
        )
        for _ in range(7)
    ]
    assert responses[-1].status_code == 429
    assert responses[-1].headers["retry-after"] == "60"


def test_ai_audit_is_non_sensitive_and_authenticated() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    init_data = _init_data({"id": 46, "first_name": "Audit"})
    lookup = client.post(
        "/api/v1/lookup",
        json={"init_data": init_data, "target": "+33142345678"},
    )
    analysis_id = lookup.json()["analysis_id"]
    response = client.post(
        "/api/v1/ai-analysis",
        json={"init_data": init_data, "analysis_id": analysis_id},
    )
    assert response.status_code == 200
    audit = client.post("/api/v1/ai-audit", json={"init_data": init_data})
    assert audit.status_code == 200
    body = audit.json()
    encoded = json.dumps(body, ensure_ascii=False)
    assert "+33142345678" not in encoded
    assert all("user_id" not in item for item in body["items"])\n    assert all("target" not in item for item in body["items"])


def test_ai_audit_isolated_between_users() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    first = _init_data({"id": 47, "first_name": "First"})
    second = _init_data({"id": 48, "first_name": "Second"})
    lookup = client.post(
        "/api/v1/lookup",
        json={"init_data": first, "target": "+33142345678"},
    )
    analysis_id = lookup.json()["analysis_id"]
    response = client.post(
        "/api/v1/ai-analysis",
        json={"init_data": first, "analysis_id": analysis_id},
    )
    assert response.status_code == 200
    first_audit = client.post("/api/v1/ai-audit", json={"init_data": first})
    second_audit = client.post("/api/v1/ai-audit", json={"init_data": second})
    assert first_audit.status_code == 200
    assert second_audit.status_code == 200
    assert len(first_audit.json()["items"]) == 1
    assert second_audit.json()["items"] == []


def test_ai_analysis_rejects_unknown_snapshot() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    init_data = _init_data({"id": 44, "first_name": "Missing"})
    response = client.post(
        "/api/v1/ai-analysis",
        json={"init_data": init_data, "analysis_id": "ali-missing"},
    )
    assert response.status_code == 404


def test_lookup_identity_is_unknown_without_authorized_provider() -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN)))
    init_data = _init_data({"id": 50, "first_name": "Identity"})
    response = client.post(
        "/api/v1/lookup",
        json={"init_data": init_data, "target": "+33142345678"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["identity"]["status"] == "not_established"
    assert payload["identity"]["name"] is None
    assert payload["identity_provider_registry"][0]["enabled"] is False


def test_identity_provider_registry_isolated_and_business_only() -> None:
    from aliali.api.identity import TwilioCallerNameProvider, build_identity_registry

    registry = build_identity_registry()
    assert all(not item["enabled"] for item in registry.policy())

    provider = TwilioCallerNameProvider("ACtest", "token")
    provider_result = provider
    assert provider_result.id == "twilio_cnam"


def test_voice_token_requires_provider_configuration(tmp_path) -> None:
    client = TestClient(create_app(Settings(bot_token=BOT_TOKEN, location_db_path=str(tmp_path / "locations.db"))))
    init_data = _init_data({"id": 70, "first_name": "Voice"})
    response = client.post("/api/v1/voice/token", json={"init_data": init_data})
    assert response.status_code == 503


def test_location_store_is_one_time_and_expires(tmp_path) -> None:
    from aliali.api.communications import LocationStore

    store = LocationStore(str(tmp_path / "locations.db"))
    request_id, token, _ = store.create(71, ttl_seconds=900)
    assert store.get(request_id, 71)["status"] == "pending"
    assert store.submit(token, 48.8566, 2.3522, 12.5) is True
    assert store.submit(token, 48.8566, 2.3522, 12.5) is False
    result = store.get(request_id, 71)
    assert result["status"] == "located"
    assert result["latitude"] == 48.8566
    assert result["longitude"] == 2.3522
    assert result["accuracy_m"] == 12.5
    assert store.get(request_id, 72) is None
