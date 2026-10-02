from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class LocationEvidence:
    status: str
    precision: str
    country: str | None
    region_code: str | None
    geographic_area: str | None
    timezones: tuple[str, ...]
    source: str
    checked_at: str
    note: str


def resolve_phone_location(
    *,
    country: str | None,
    region_code: str | None,
    geographic_area: str | None,
    timezones: list[str],
    source: str,
) -> LocationEvidence:
    checked_at = datetime.now(UTC).isoformat()
    if geographic_area:
        precision = "PHONE_AREA"
        note = (
            "هذه منطقة جغرافية مرتبطة ببيانات الرقم وليست عنوانًا دقيقًا "
            "ولا موقعًا حاليًا للجهاز."
        )
        status = "available"
    elif region_code or country:
        precision = "PHONE_REGION"
        note = (
            "هذه منطقة ترقيم مرتبطة بالرقم. لا تمثل موقعًا حاليًا للجهاز "
            "ولا نقطة GPS."
        )
        status = "available"
    else:
        precision = "UNKNOWN"
        note = "لم تتوفر إشارة جغرافية موثوقة من metadata الرقم."
        status = "unknown"

    return LocationEvidence(
        status=status,
        precision=precision,
        country=country,
        region_code=region_code,
        geographic_area=geographic_area,
        timezones=tuple(timezones),
        source=source,
        checked_at=checked_at,
        note=note,
    )


def as_dict(evidence: LocationEvidence) -> dict[str, object]:
    return {
        "status": evidence.status,
        "precision": evidence.precision,
        "country": evidence.country,
        "region_code": evidence.region_code,
        "geographic_area": evidence.geographic_area,
        "timezones": list(evidence.timezones),
        "source": evidence.source,
        "checked_at": evidence.checked_at,
        "note": evidence.note,
        "coordinates": None,
    }
