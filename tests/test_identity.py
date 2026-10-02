from __future__ import annotations

import json

from aliali.api import identity


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def test_twilio_business_name_is_accepted(monkeypatch):
    monkeypatch.setattr(
        identity,
        "urlopen",
        lambda request, timeout: FakeResponse(
            {"caller_name": {"caller_name": "Example GmbH", "caller_type": "BUSINESS"}}
        ),
    )
    provider = identity.TwilioCallerNameProvider("ACtest", "secret")
    result = provider.lookup("+12025550123")
    assert result.status == "verified_business"
    assert result.name == "Example GmbH"
    assert result.association_type == "business"


def test_twilio_consumer_name_is_not_exposed(monkeypatch):
    monkeypatch.setattr(
        identity,
        "urlopen",
        lambda request, timeout: FakeResponse(
            {"caller_name": {"caller_name": "Private Person", "caller_type": "CONSUMER"}}
        ),
    )
    provider = identity.TwilioCallerNameProvider("ACtest", "secret")
    result = provider.lookup("+12025550123")
    assert result.status == "not_established"
    assert result.name is None


def test_identity_conflict_never_selects_a_winner():
    class Provider:
        id = "p"
        name = "Provider"
        method = "authorized_provider"

        def lookup(self, phone_e164):
            return identity.IdentityResult(
                self.id, self.name, "verified_business", "One", "business",
                "test", "2026-01-01T00:00:00+00:00", None, self.method, "test"
            )

    class ProviderTwo(Provider):
        id = "p2"
        name = "Provider Two"

        def lookup(self, phone_e164):
            return identity.IdentityResult(
                self.id, self.name, "verified_business", "Two", "business",
                "test", "2026-01-01T00:00:00+00:00", None, self.method, "test"
            )

    registry = identity.IdentityProviderRegistry(
        (
            identity.IdentityProviderRegistration(Provider(), enabled=True),
            identity.IdentityProviderRegistration(ProviderTwo(), enabled=True),
        )
    )
    resolved, _ledger = identity.resolve_identity("+12025550123", registry)
    assert resolved["status"] == "conflict"
    assert resolved["name"] is None
