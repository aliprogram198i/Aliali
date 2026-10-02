from aliali.api.phone import _lookup_phone
from aliali.api.social import (
    EvidenceLedger,
    ProviderRegistration,
    SocialProviderRegistry,
    SocialResult,
    check_social_presence,
    check_social_presence_with_ledger,
)


def test_social_results_never_claim_presence_without_authorized_evidence() -> None:
    result = _lookup_phone("+33142345678")
    apps = result["social_apps"]
    assert {app["id"] for app in apps} == {"whatsapp", "telegram", "signal", "linkedin"}
    assert all(app["status"] == "provider_unavailable" for app in apps)
    assert all(app["verification"] == "not_verified" for app in apps)
    assert all(app["source"] is None for app in apps)
    assert all(app["evidence"] is None for app in apps)


def test_social_summary_preserves_evidence_gate() -> None:
    result = _lookup_phone("+33142345678")
    assert all(item["status"] == "provider_unavailable" for item in result["social_summary"])
    assert all(item["source"] is None for item in result["social_summary"])


def test_social_adapter_failure_is_isolated(monkeypatch) -> None:
    from aliali.api import social

    class BrokenProvider:
        id = "broken"
        name = "Broken"
        method = "authorized_provider"

        def check(self, phone_e164: str) -> SocialResult:
            raise RuntimeError("simulated provider failure")

    existing = social._REGISTRY.all()
    monkeypatch.setattr(
        social,
        "_REGISTRY",
        SocialProviderRegistry(
            (
                ProviderRegistration(BrokenProvider(), enabled=True),
                *existing,
            )
        ),
    )
    results = check_social_presence("+33142345678")
    assert results[0]["status"] == "provider_unavailable"
    assert "عزل الخطأ" in results[0]["note"]
    assert len(results) == 5


def test_social_adapter_boundary_accepts_normalized_number_without_storing_it() -> None:
    results, ledger = check_social_presence_with_ledger("+33142345678")
    assert all(item["source"] is None for item in results)
    assert all(item["evidence"] is None for item in results)
    assert all("phone" not in entry for entry in ledger)


def test_evidence_ledger_records_only_result_evidence() -> None:
    ledger = EvidenceLedger()
    result = SocialResult(
        id="example",
        name="Example",
        status="verified_present",
        verification="verified",
        source="authorized_provider",
        checked_at="2026-10-02T00:00:00+00:00",
        evidence={"proof": "provider-confirmed"},
        method="authorized_provider",
        note="verified by authorized evidence",
    )
    ledger.record(result)
    assert ledger.as_dicts() == [
        {
            "provider_id": "example",
            "status": "verified_present",
            "verification": "verified",
            "source": "authorized_provider",
            "checked_at": "2026-10-02T00:00:00+00:00",
            "evidence": {"proof": "provider-confirmed"},
            "method": "authorized_provider",
            "note": "verified by authorized evidence",
        }
    ]


def test_provider_registry_rejects_duplicate_ids_and_invalid_policy() -> None:
    class Provider:
        id = "example"
        name = "Example"
        method = "authorized_provider"

        def check(self, phone_e164: str) -> SocialResult:
            raise AssertionError("not called")

    registry = SocialProviderRegistry()
    registry.register(ProviderRegistration(Provider()))
    try:
        registry.register(ProviderRegistration(Provider()))
    except ValueError as exc:
        assert "Duplicate provider id" in str(exc)
    else:
        raise AssertionError("duplicate provider id must fail")

    for timeout, rate in ((0, 30), (5, 0)):
        try:
            ProviderRegistration(Provider(), timeout_seconds=timeout, max_calls_per_minute=rate)
            if timeout > 0:
                raise AssertionError("invalid rate limit must fail at registration")
        except ValueError:
            pass
