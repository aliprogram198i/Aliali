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


_PROVIDERS: tuple[SocialProviderAdapter, ...] = (
    UnavailableProvider("whatsapp", "WhatsApp", "authorized_provider"),
    UnavailableProvider("telegram", "Telegram", "authorized_provider"),
    UnavailableProvider("signal", "Signal", "authorized_provider"),
    UnavailableProvider("linkedin", "LinkedIn", "public_association"),
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


def check_social_presence(phone_e164: str | None = None) -> list[dict[str, object]]:
    """Run isolated adapters and never infer account presence."""
    phone = phone_e164 or ""
    results: list[dict[str, object]] = []
    for provider in _PROVIDERS:
        try:
            results.append(_serialize(provider.check(phone)))
        except Exception:
            results.append(
                _serialize(
                    SocialResult(
                        id=provider.id,
                        name=provider.name,
                        status="provider_unavailable",
                        verification="not_verified",
                        source=None,
                        checked_at=None,
                        evidence=None,
                        method=provider.method,
                        note="تعذر تشغيل مزود التحقق؛ تم عزل الخطأ ولم تتأثر بقية النتائج.",
                    )
                )
            )
    return results
