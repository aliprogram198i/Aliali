from aliali.api.phone import _lookup_phone


def test_lookup_phone_international_number():
    result = _lookup_phone("+33142345678")
    assert result["type"] == "phone"
    assert result["valid"] is True
    assert result["country_code"] == 33
    assert result["region_code"] == "FR"
    assert result["e164"] == "+33142345678"
    assert result["line_type"]


def test_lookup_phone_rejects_invalid_format():
    try:
        _lookup_phone("not-a-phone")
    except ValueError as exc:
        assert "رقم هاتف" in str(exc)
    else:
        raise AssertionError("invalid input should fail")
