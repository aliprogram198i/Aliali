import asyncio
import json

from aliali.ai import (
    analyze_with_openai,
    build_ai_payload,
    create_evidence_snapshot,
    detect_conflicts,
    verify_analysis,
)
from aliali.config import Settings


def _result():
    return {
        "target": "+33142345678",
        "valid": True,
        "possible": True,
        "country_name": "France",
        "country_code": 33,
        "region_code": "FR",
        "line_type": "هاتف محمول",
        "carrier": "Example Carrier",
        "location": "Paris",
        "timezones": ["Europe/Paris"],
        "evidence": {
            "items": [
                {"field": "validity", "value": "valid", "confidence": "high", "kind": "public_metadata"},
                {"field": "country", "value": "France", "confidence": "high", "kind": "public_metadata"},
            ],
            "limitations": ["No live location."],
        },
        "unknown": ["هوية صاحب الرقم", "الموقع الحالي للجهاز"],
        "consistency_checks": [],
        "coverage": {"percent": 80},
    }


def test_ai_payload_never_contains_raw_phone_number():
    encoded = json.dumps(build_ai_payload(_result()), ensure_ascii=False)
    assert "+33142345678" not in encoded
    assert "target" not in build_ai_payload(_result())


def test_snapshot_is_identifying_data_free_and_versioned():
    snapshot = create_evidence_snapshot(_result())
    encoded = json.dumps(snapshot, ensure_ascii=False)
    assert "+33142345678" not in encoded
    assert snapshot["analysis_id"].startswith("ali-")
    assert snapshot["payload"]["policy_version"] == "3.0"
    assert snapshot["payload"]["evidence_schema_version"] == "2.0"


def test_conflicts_are_detected_without_choosing_a_winner():
    payload = build_ai_payload(_result())
    payload["evidence"]["evidence_items"].append(
        {"id": "E3", "field": "country", "value": "Belgium", "confidence": "medium"}
    )
    conflicts = detect_conflicts(payload)
    assert conflicts[0]["field"] == "country"
    assert conflicts[0]["status"] == "unresolved"


def test_verifier_requires_supported_claims():
    payload = build_ai_payload(_result())
    analysis = {
        "claims": [
            {"claim": "owner identity is Ali", "support": [], "confidence": "high"},
        ]
    }
    result = verify_analysis(analysis, payload)
    assert result["verified"] is False
    assert "unsupported_sensitive_claim" in result["violations"]


def test_ai_disabled_returns_verified_deterministic_analysis():
    result = asyncio.run(analyze_with_openai(_result(), Settings(bot_token="x")))
    assert result["status"] == "deterministic_only"
    assert result["verification"]["verified"] is True
    assert result["analysis"]["claims"]


def test_ai_provider_error_falls_back_to_deterministic(monkeypatch):
    from aliali import ai

    def fail(*args, **kwargs):
        raise TimeoutError("timeout")

    monkeypatch.setattr(ai.request, "urlopen", fail)
    settings = Settings(bot_token="x", ai_enabled=True, openai_api_key="test")
    result = asyncio.run(analyze_with_openai(_result(), settings))
    assert result["status"] == "provider_error"
    assert result["analysis"]["claims"]
