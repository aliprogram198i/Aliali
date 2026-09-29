from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    actor_id: int
    module_key: str
    timestamp: datetime
    success: bool
    metadata: dict[str, Any]


def make_audit_event(
    event_type: str,
    actor_id: int,
    module_key: str,
    success: bool,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_type=event_type,
        actor_id=actor_id,
        module_key=module_key,
        timestamp=datetime.now(UTC),
        success=success,
        metadata=metadata or {},
    )
