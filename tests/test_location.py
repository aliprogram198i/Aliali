from aliali.api.location import resolve_phone_location


def test_phone_area_is_explicitly_non_live():
    result = resolve_phone_location(
        country="France",
        region_code="FR",
        geographic_area="Paris",
        timezones=["Europe/Paris"],
        source="Google libphonenumber metadata",
    )
    assert result.precision == "PHONE_AREA"
    assert result.status == "available"
    assert "GPS" in result.note
    assert result.timezones == ("Europe/Paris",)


def test_location_falls_back_to_phone_region():
    result = resolve_phone_location(
        country="France",
        region_code="FR",
        geographic_area=None,
        timezones=[],
        source="Google libphonenumber metadata",
    )
    assert result.precision == "PHONE_REGION"
    assert result.coordinates is None if hasattr(result, "coordinates") else True
