from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from .network_identity import AssetIdentity


class EvidenceKind(StrEnum):
    OBSERVED = "observed"
    VERIFIED = "verified"
    INFERRED = "inferred"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source: str
    field: str
    value: str
    kind: EvidenceKind
    confidence: Confidence
    observed_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NetworkGeolocation:
    country: str | None = None
    region: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    isp: str | None = None
    asn: str | None = None
    source: str | None = None
    confidence: Confidence = Confidence.LOW
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_estimate(self) -> bool:
        return True


@dataclass(frozen=True)
class AssetChange:
    field: str
    previous_value: str | None
    current_value: str | None
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class NetworkAssetProfile:
    asset_id: str
    identity: AssetIdentity
    device_type: str | None = None
    services: tuple[str, ...] = ()
    protocols: tuple[str, ...] = ()
    geolocation: NetworkGeolocation | None = None
    evidence: list[Evidence] = field(default_factory=list)
    changes: list[AssetChange] = field(default_factory=list)

    def add_evidence(self, item: Evidence) -> None:
        self.evidence.append(item)

    def add_change(self, change: AssetChange) -> None:
        self.changes.append(change)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def confidence(self) -> Confidence:
        if not self.evidence:
            return Confidence.LOW
        levels = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
        average = sum(levels[item.confidence] for item in self.evidence) / len(self.evidence)
        if average >= 1.5:
            return Confidence.HIGH
        if average >= 0.75:
            return Confidence.MEDIUM
        return Confidence.LOW
