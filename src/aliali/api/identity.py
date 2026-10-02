from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

IdentityStatus = Literal["verified_business", "verified_user_consent", "publicly_associated", "not_established", "provider_unavailable", "conflict"]


@dataclass(frozen=True)
class IdentityResult:
    provider_id: str
    provider_name: str
    status: IdentityStatus
    name: str | None
    association_type: str | None
    source: str | None
    checked_at: str | None
    evidence: dict[str, object] | None
    method: str
    note: str


@dataclass(frozen=True)
class IdentityProviderRegistration:
    provider: object
    enabled: bool = False
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class UnavailableIdentityProvider:
    id: str
    name: str
    method: str

    def lookup(self, phone_e164: str) -> IdentityResult:
        del phone_e164
        return IdentityResult(self.id, self.name, "provider_unavailable", None, None, None, None, None, self.method, "مزود الهوية غير مفعل؛ لا يتم استنتاج اسم من بيانات الرقم.")


class TwilioCallerNameProvider:
    id = "twilio_cnam"
    name = "Twilio Caller Name (CNAM)"
    method = "authorized_provider"

    def __init__(self, account_sid: str, auth_token: str, timeout_seconds: float = 5.0) -> None:
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._timeout_seconds = timeout_seconds

    def lookup(self, phone_e164: str) -> IdentityResult:
        checked_at = datetime.now(UTC).isoformat()
        url = f"https://lookups.twilio.com/v2/PhoneNumbers/{phone_e164}?Fields=caller_name"
        credentials = base64.b64encode(f"{self._account_sid}:{self._auth_token}".encode()).decode()
        request = Request(url, headers={"Authorization": f"Basic {credentials}", "Accept": "application/json"}, method="GET")
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError):
            return IdentityResult(self.id, self.name, "provider_unavailable", None, None, None, checked_at, None, self.method, "تعذر الوصول إلى مزود CNAM؛ تم عزل فشل المزود.")

        caller_name = payload.get("caller_name")
        if not isinstance(caller_name, dict):
            return IdentityResult(self.id, self.name, "not_established", None, None, "Twilio CNAM", checked_at, {"provider": self.id, "available": False}, self.method, "لم يُرجع مزود CNAM اسمًا قابلًا للاعتماد.")

        name = caller_name.get("caller_name")
        caller_type = caller_name.get("caller_type")
        if not isinstance(name, str) or not name.strip() or caller_type != "BUSINESS":
            return IdentityResult(self.id, self.name, "not_established", None, None, "Twilio CNAM", checked_at, {"provider": self.id, "caller_type": caller_type, "available": bool(name)}, self.method, "لم يتم عرض اسم شخص خاص؛ لا يُعامل Consumer CNAM كهوية شخصية موثقة.")

        return IdentityResult(self.id, self.name, "verified_business", name.strip(), "business", "Twilio CNAM", checked_at, {"provider": self.id, "caller_type": "BUSINESS", "verification": "carrier_cnam"}, self.method, "اسم تجاري أعاده مصدر CNAM مصرح به؛ لا يمثل موقعًا حاليًا.")


class IdentityProviderRegistry:
    def __init__(self, registrations: tuple[IdentityProviderRegistration, ...]) -> None:
        self._registrations: dict[str, IdentityProviderRegistration] = {}
        for registration in registrations:
            if registration.provider.id in self._registrations:
                raise ValueError(f"Duplicate identity provider id: {registration.provider.id}")
            if registration.timeout_seconds <= 0:
                raise ValueError("Identity provider timeout must be positive.")
            self._registrations[registration.provider.id] = registration

    def all(self) -> tuple[IdentityProviderRegistration, ...]:
        return tuple(self._registrations.values())

    def enabled(self) -> tuple[IdentityProviderRegistration, ...]:
        return tuple(item for item in self._registrations.values() if item.enabled)

    def policy(self) -> list[dict[str, object]]:
        return [{"id": x.provider.id, "name": x.provider.name, "method": x.provider.method, "enabled": x.enabled, "timeout_seconds": x.timeout_seconds} for x in self._registrations.values()]


def build_identity_registry(*, twilio_account_sid: str | None = None, twilio_auth_token: str | None = None) -> IdentityProviderRegistry:
    registrations = [IdentityProviderRegistration(UnavailableIdentityProvider("public_business_association", "Public Business Association", "public_association"), enabled=False)]
    if twilio_account_sid and twilio_auth_token:
        registrations.append(IdentityProviderRegistration(TwilioCallerNameProvider(twilio_account_sid, twilio_auth_token), enabled=True))
    else:
        registrations.append(IdentityProviderRegistration(UnavailableIdentityProvider("twilio_cnam", "Twilio Caller Name (CNAM)", "authorized_provider"), enabled=False))
    return IdentityProviderRegistry(tuple(registrations))


def resolve_identity(phone_e164: str, registry: IdentityProviderRegistry) -> tuple[dict[str, object], list[dict[str, object]]]:
    results: list[IdentityResult] = []
    for registration in registry.enabled():
        try:
            results.append(registration.provider.lookup(phone_e164))
        except Exception:  # noqa: BLE001
            results.append(IdentityResult(registration.provider.id, registration.provider.name, "provider_unavailable", None, None, None, None, None, registration.provider.method, "تعذر تشغيل مزود الهوية؛ تم عزل الخطأ."))

    verified = [x for x in results if x.status in {"verified_business", "verified_user_consent", "publicly_associated"} and x.name]
    names = {x.name for x in verified}
    if len(names) > 1:
        identity = {"status": "conflict", "name": None, "source": None, "verified_at": None, "association_type": None, "note": "مصادر الهوية أعادت ارتباطات مختلفة؛ لم يتم اختيار اسم على حساب آخر."}
    elif verified:
        x = verified[0]
        identity = {"status": x.status, "name": x.name, "source": x.source, "verified_at": x.checked_at, "association_type": x.association_type, "note": x.note}
    else:
        identity = {"status": "not_established", "name": None, "source": None, "verified_at": None, "association_type": None, "note": "لا توجد هوية عامة أو مصرح بها قابلة للتحقق في المصادر المفعلة."}

    ledger = [{"provider_id": x.provider_id, "provider_name": x.provider_name, "status": x.status, "name": x.name, "association_type": x.association_type, "source": x.source, "checked_at": x.checked_at, "evidence": x.evidence, "method": x.method, "note": x.note} for x in results]
    return identity, ledger
