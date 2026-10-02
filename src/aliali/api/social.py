from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SocialStatus = Literal[
    "verified_present",
    "verified_absent",
    "privacy_blocked",
    "provider_unavailable",
    "not_checked",
]

@dataclass(frozen=True)
class SocialProvider:
    id: str
    name: str
    method: str

_PROVIDERS = (
    SocialProvider("whatsapp", "WhatsApp", "authorized_provider"),
    SocialProvider("telegram", "Telegram", "authorized_provider"),
    SocialProvider("signal", "Signal", "authorized_provider"),
    SocialProvider("linkedin", "LinkedIn", "public_association"),
)

def check_social_presence() -> list[dict[str, object]]:
    """Return only evidence states that can be justified by an authorized source.

    No platform is queried by scraping, enumeration, leaked data, or guessed account
    identifiers. Until an authorized provider is configured, the result is explicit
    provider_unavailable rather than a false positive/negative.
    """
    return [
        {
            "id": provider.id,
            "name": provider.name,
            "status": "provider_unavailable",
            "verification": "not_verified",
            "source": None,
            "checked_at": None,
            "evidence": None,
            "note": (
                "لا يوجد مزود مصرح ومتاح للتحقق من ارتباط الرقم بهذه المنصة؛ "
                "لذلك لا يتم استنتاج وجود الحساب أو عدمه."
            ),
            "method": provider.method,
        }
        for provider in _PROVIDERS
    ]
