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


def test_lookup_phone_exposes_contact_channel_states():
    result = _lookup_phone("+33142345678")
    channels = {item["id"]: item for item in result["social_apps"]}
    assert {"whatsapp", "telegram", "other"} <= channels.keys()
    assert channels["whatsapp"]["status"] == "number_contact_supported"
    assert channels["telegram"]["status"] == "privacy_dependent"
    assert channels["other"]["status"] == "not_verifiable_from_number"
