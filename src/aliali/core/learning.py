from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LearningSignal:
    module_key: str
    outcome: str
    confidence: float
    evidence: dict[str, Any]
    created_at: datetime


class LearningEngine:
    """Collects reviewed outcomes; it never self-modifies production code."""

    def __init__(self) -> None:
        self._signals: list[LearningSignal] = []

    def record(
        self,
        module_key: str,
        outcome: str,
        confidence: float,
        evidence: dict[str, Any] | None = None,
    ) -> LearningSignal:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        signal = LearningSignal(
            module_key=module_key,
            outcome=outcome,
            confidence=confidence,
            evidence=evidence or {},
            created_at=datetime.now(timezone.utc),
        )
        self._signals.append(signal)
        return signal

    def signals(self) -> tuple[LearningSignal, ...]:
        return tuple(self._signals)
