from aliali.ai import analyze_evidence


def test_ai_disabled_never_calls_provider():
    result = analyze_evidence(
        evidence={"valid": True, "line_type": "هاتف محمول", "evidence": {"items": []}},
        api_key=None,
        model="gpt-5.6-luna",
        enabled=False,
    )
    assert result["status"] == "disabled"
    assert result["provider"] is None


def test_ai_requires_key_when_enabled():
    try:
        analyze_evidence(
            evidence={"valid": True, "evidence": {"items": []}},
            api_key=None,
            model="gpt-5.6-luna",
            enabled=True,
        )
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected AI configuration failure")
