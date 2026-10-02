from aliali.api.phone import _lookup_phone


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
