from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

SocialStatus = Literal[
    "verified_present",
    "verified_absent",
    "privacy_blocked",
    "provider_unavailable",
    "not_checked",
]
Verification = Literal["verified", "not_verified"]


@dataclass(frozen=True)
class SocialResult:
    id: str
    name: str
    status: SocialStatus
    verification: Verification
    source: str | None
    checked_at: str | None
    evidence: dict[str, object] | None
    method: str
    note: str


class SocialProviderAdapter(Protocol):
    id: str
    name: str
    method: str

    def check(self, phone_e164: str) -> SocialResult: ...


@dataclass(frozen=True)
class ProviderRegistration:
    adapter: SocialProviderAdapter
    enabled: bool = False
    timeout_seconds: float = 5.0
    max_calls_per_minute: int = 30


@dataclass(frozen=True)
class EvidenceLedgerEntry:
    provider_id: str
    status: SocialStatus
    verification: Verification
    source: str | None
    checked_at: str | None
    evidence: dict[str, object] | None
    method: str
    note: str


class EvidenceLedger:
    """Request-scoped evidence ledger; it never stores the queried phone number."""

    def __init__(self) -> None:
        self._entries: list[EvidenceLedgerEntry] = []

    def record(self, result: SocialResult) -> None:
        self._entries.append(
            EvidenceLedgerEntry(
                provider_id=result.id,
                status=result.status,
                verification=result.verification,
                source=result.source,
                checked_at=result.checked_at,
                evidence=result.evidence,
                method=result.method,
                note=result.note,
            )
        )

    def as_dicts(self) -> list[dict[str, object]]:
        return [
            {
                "provider_id": entry.provider_id,
                "status": entry.status,
                "verification": entry.verification,
                "source": entry.source,
                "checked_at": entry.checked_at,
                "evidence": entry.evidence,
                "method": entry.method,
                "note": entry.note,
            }
            for entry in self._entries
        ]


class SocialProviderRegistry:
    """Deterministic registry for authorized/public social verification adapters."""

    def __init__(self, registrations: tuple[ProviderRegistration, ...] = ()) -> None:
        self._registrations: dict[str, ProviderRegistration] = {}
        for registration in registrations:
            self.register(registration)

    def register(self, registration: ProviderRegistration) -> None:
        provider_id = registration.adapter.id
        if not provider_id:
            raise ValueError("Provider id cannot be empty.")
        if provider_id in self._registrations:
            raise ValueError(f"Duplicate provider id: {provider_id}")
        if registration.timeout_seconds <= 0:
            raise ValueError("Provider timeout must be positive.")
        if registration.max_calls_per_minute <= 0:
            raise ValueError("Provider rate limit must be positive.")
        self._registrations[provider_id] = registration

    def enabled(self) -> tuple[ProviderRegistration, ...]:
        return tuple(item for item in self._registrations.values() if item.enabled)

    def all(self) -> tuple[ProviderRegistration, ...]:
        return tuple(self._registrations.values())

    def policy(self) -> list[dict[str, object]]:
        return [
            {
                "id": item.adapter.id,
                "name": item.adapter.name,
                "method": item.adapter.method,
                "enabled": item.enabled,
                "timeout_seconds": item.timeout_seconds,
                "max_calls_per_minute": item.max_calls_per_minute,
            }
            for item in self._registrations.values()
        ]


@dataclass(frozen=True)
class UnavailableProvider:
    id: str
    name: str
    method: str

    def check(self, phone_e164: str) -> SocialResult:
        del phone_e164
        return SocialResult(
            id=self.id,
            name=self.name,
            status="provider_unavailable",
            verification="not_verified",
            source=None,
            checked_at=None,
            evidence=None,
            method=self.method,
            note=(
                "لا يوجد مزود مصرح ومتاح حاليًا للتحقق من ارتباط الرقم بهذه المنصة؛ "
                "لذلك لا يتم استنتاج وجود الحساب أو عدمه."
            ),
        )


_REGISTRY = SocialProviderRegistry(
    tuple(
        ProviderRegistration(
            UnavailableProvider(provider_id, name, method),
            enabled=False,
        )
        for provider_id, name, method in (
            ("whatsapp", "WhatsApp", "authorized_provider"),
            ("telegram", "Telegram", "authorized_provider"),
            ("signal", "Signal", "authorized_provider"),
            ("linkedin", "LinkedIn", "public_association"),
        )
    )
)

# Compatibility view for tests/integrations that inspect the provider collection.
_PROVIDERS: tuple[SocialProviderAdapter, ...] = tuple(
    registration.adapter for registration in _REGISTRY.all()
)


def _serialize(result: SocialResult) -> dict[str, object]:
    return {
        "id": result.id,
        "name": result.name,
        "status": result.status,
        "verification": result.verification,
        "source": result.source,
        "checked_at": result.checked_at,
        "evidence": result.evidence,
        "method": result.method,
        "note": result.note,
    }


def _fallback_result(provider: SocialProviderAdapter, note: str) -> SocialResult:
    return SocialResult(
        id=provider.id,
        name=provider.name,
        status="provider_unavailable",
        verification="not_verified",
        source=None,
        checked_at=None,
        evidence=None,
        method=provider.method,
        note=note,
    )


def check_social_presence(
    phone_e164: str | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Run registered adapters and return both user results and request-scoped evidence."""
    phone = phone_e164 or ""
    results: list[dict[str, object]] = []
    ledger = EvidenceLedger()

    for registration in _REGISTRY.all():
        provider = registration.adapter
        if not registration.enabled:
            result = provider.check(phone)
        else:
            # Real providers are deliberately disabled until an authorized integration
            # is configured. Enabled adapters must implement their own bounded client.
            result = provider.check(phone)
        ledger.record(result)
        results.append(_serialize(result))

    return results, ledger.as_dicts()
