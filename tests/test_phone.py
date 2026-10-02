from aliali.api.phone import _lookup_phone


def test_lookup_phone_international_number():
    result = _lookup_phone("+33142345678")
    assert result["type"] == "phone"
    assert result["valid"] is True
    assert result["possible"] is True
    assert result["country_code"] == 33
    assert result["region_code"] == "FR"
    assert result["e164"] == "+33142345678"
    assert result["line_type"]
    assert result["analysis"]["status"] == "verified_public_metadata"
    assert result["analysis"]["overall_confidence"] == "high"
    assert result["analysis"]["evidence_count"] >= 4
    assert result["evidence"]["metadata_version"]
    assert result["evidence"]["items"]


def test_lookup_phone_rejects_invalid_format():
    try:
        _lookup_phone("not-a-phone")
    except ValueError as exc:
        assert "رقم هاتف" in str(exc)
    else:
        raise AssertionError("invalid input should fail")


def test_lookup_phone_accepts_arabic_digits_without_persisting_input():
    result = _lookup_phone("+٣٣١٤٢٣٤٥٦٧٨")
    assert result["e164"] == "+33142345678"
    assert result["target"] == "+33142345678"


def test_lookup_phone_exposes_professional_intelligence_layers():
    result = _lookup_phone("+33142345678")

    assert result["executive_summary"]["validity"] == "confirmed"
    assert 0 <= result["coverage"]["percent"] <= 100
    assert result["confidence"]["overall"] == "high"
    assert len(result["source_registry"]) >= 3
    assert len(result["consistency_checks"]) == 3
    assert result["ai_analysis"]["status"] == "evidence_first"
    assert result["ai_analysis"]["provider"] is None
    assert result["unknown"]
    assert len(result["timeline"]) == 4
