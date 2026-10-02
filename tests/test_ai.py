import asyncio
import json

from aliali.ai import analyze_with_openai, build_ai_payload
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
        "evidence": {"items": [{"field": "validity", "value": "valid", "confidence": "high"}], "limitations": ["No live location."]},
    }


def test_ai_payload_never_contains_raw_phone_number():
    encoded = json.dumps(build_ai_payload(_result()), ensure_ascii=False)
    assert "+33142345678" not in encoded
    assert "target" not in build_ai_payload(_result())


def test_ai_disabled_by_default():
    result = asyncio.run(analyze_with_openai(_result(), Settings(bot_token="x")))
    assert result["status"] == "disabled"
