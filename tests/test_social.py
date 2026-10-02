from aliali.api.phone import _lookup_phone
from aliali.api.social import SocialResult, check_social_presence


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

    monkeypatch.setattr(social, "_PROVIDERS", (BrokenProvider(), *social._PROVIDERS))
    results = check_social_presence("+33142345678")
    assert results[0]["status"] == "provider_unavailable"
    assert "عزل الخطأ" in results[0]["note"]
    assert len(results) == 5


def test_social_adapter_boundary_accepts_normalized_number_without_storing_it() -> None:
    results = check_social_presence("+33142345678")
    assert all(item["source"] is None for item in results)
    assert all(item["evidence"] is None for item in results)
