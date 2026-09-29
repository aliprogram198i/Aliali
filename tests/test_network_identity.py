import pytest

from aliali.core.network_identity import (
    AssetIdentity,
    NetworkIdentifier,
    NetworkIdentifierType,
)


@pytest.mark.parametrize(
    ("value", "expected_type", "expected_value"),
    [
        ("192.168.1.10", NetworkIdentifierType.IP, "192.168.1.10"),
        ("2001:db8::1", NetworkIdentifierType.IP, "2001:db8::1"),
        ("AA:BB:CC:DD:EE:FF", NetworkIdentifierType.MAC, "aa:bb:cc:dd:ee:ff"),
        ("aa-bb-cc-dd-ee-ff", NetworkIdentifierType.MAC, "aa:bb:cc:dd:ee:ff"),
    ],
)
def test_network_identifier_parses_ip_and_mac(value, expected_type, expected_value):
    identifier = NetworkIdentifier.parse(value)
    assert identifier.identifier_type == expected_type
    assert identifier.value == expected_value


@pytest.mark.parametrize("value", ["", "not-an-ip", "aa:bb:cc:dd:ee"])
def test_network_identifier_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        NetworkIdentifier.parse(value)


def test_asset_identity_normalizes_mac_and_accepts_mac_only():
    asset = AssetIdentity(mac="AA-BB-CC-DD-EE-FF")
    assert asset.mac == "aa:bb:cc:dd:ee:ff"


def test_asset_identity_requires_ip_or_mac():
    with pytest.raises(ValueError):
        AssetIdentity()
