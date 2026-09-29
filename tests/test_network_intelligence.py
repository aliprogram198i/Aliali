from datetime import UTC, datetime

import pytest

from aliali.core.network_identity import AssetIdentity
from aliali.core.network_intelligence import (
    AssetChange,
    Confidence,
    Evidence,
    EvidenceKind,
    NetworkAssetProfile,
    NetworkGeolocation,
)


def test_network_asset_profile_tracks_evidence_and_confidence():
    profile = NetworkAssetProfile(
        asset_id="asset-1",
        identity=AssetIdentity(ip="192.168.1.10"),
    )
    profile.add_evidence(
        Evidence(
            evidence_id="e-1",
            source="dhcp",
            field="hostname",
            value="camera-lab",
            kind=EvidenceKind.OBSERVED,
            confidence=Confidence.HIGH,
            observed_at=datetime.now(UTC),
        )
    )
    profile.add_evidence(
        Evidence(
            evidence_id="e-2",
            source="arp",
            field="mac",
            value="aa:bb:cc:dd:ee:ff",
            kind=EvidenceKind.VERIFIED,
            confidence=Confidence.MEDIUM,
            observed_at=datetime.now(UTC),
        )
    )

    assert profile.evidence_count == 2
    assert profile.confidence == Confidence.HIGH


def test_network_geolocation_is_explicitly_an_estimate():
    location = NetworkGeolocation(
        country="DE",
        city="Frankfurt",
        source="geoip",
        confidence=Confidence.MEDIUM,
    )

    assert location.is_estimate is True


def test_network_asset_profile_tracks_changes():
    profile = NetworkAssetProfile(
        asset_id="asset-2",
        identity=AssetIdentity(mac="AA-BB-CC-DD-EE-FF"),
    )
    profile.add_change(
        AssetChange(
            field="hostname",
            previous_value="old-name",
            current_value="new-name",
        )
    )

    assert len(profile.changes) == 1
    assert profile.changes[0].previous_value == "old-name"


@pytest.mark.parametrize(
    "confidence, expected",
    [
        (Confidence.LOW, Confidence.LOW),
        (Confidence.MEDIUM, Confidence.MEDIUM),
        (Confidence.HIGH, Confidence.HIGH),
    ],
)
def test_single_evidence_confidence_is_preserved(confidence, expected):
    profile = NetworkAssetProfile(
        asset_id="asset-3",
        identity=AssetIdentity(ip="2001:db8::1"),
    )
    profile.add_evidence(
        Evidence(
            evidence_id="e-1",
            source="test",
            field="device_type",
            value="unknown",
            kind=EvidenceKind.INFERRED,
            confidence=confidence,
            observed_at=datetime.now(UTC),
        )
    )

    assert profile.confidence == expected
