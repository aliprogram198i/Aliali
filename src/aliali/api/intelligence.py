from __future__ import annotations

from datetime import UTC, datetime


def build_intelligence(
    *,
    checked_at: str,
    valid: bool,
    possible: bool,
    identity: dict[str, object],
    current_location: dict[str, object],
    location_profile: dict[str, object] | None = None,
    social_apps: list[dict[str, object]],
    evidence_items: list[dict[str, object]],
    source: str,
    metadata_version: str,
    identity_evidence_ledger: list[dict[str, object]] | None = None,
    identity_provider_registry: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build deterministic, evidence-first intelligence without inventing identity facts."""
    confirmed = [item for item in evidence_items if item.get("confidence") == "high"]
    supported = [item for item in evidence_items if item.get("confidence") == "medium"]
    unknowns = ["هوية صاحب الرقم", "الموقع الحالي للجهاز", "وجود حسابات اجتماعية نشطة"]

    source_registry = [
        {
            "id": "number_metadata",
            "name": source,
            "type": "numbering_metadata",
            "status": "available",
            "retrieved_at": checked_at,
            "metadata_version": metadata_version,
        },
        {
            "id": "identity",
            "name": identity.get("source") or "لا يوجد مصدر هوية",
            "type": "identity",
            "status": "verified" if identity.get("status") in {"verified_business", "verified_user_consent", "publicly_associated"} else "not_available",
            "retrieved_at": identity.get("verified_at"),
        },
        {
            "id": "current_location",
            "name": current_location.get("source") or "لا يوجد مصدر موقع",
            "type": "live_location",
            "status": "available" if current_location.get("status") == "live" else "not_available",
            "retrieved_at": current_location.get("updated_at"),
        },
    ]

    consistency_checks = [
        {
            "id": "number_validity",
            "label": "اتساق صلاحية الرقم",
            "status": "consistent" if valid else "insufficient",
            "details": "تتوافق بيانات البنية مع metadata العامة." if valid else "لم تثبت metadata العامة صلاحية الرقم.",
        },
        {
            "id": "identity_consistency",
            "label": "اتساق الهوية",
            "status": "not_assessed",
            "details": "لا توجد أدلة هوية كافية للمقارنة." if identity.get("status") == "not_established" else "تحتاج الهوية إلى مقارنة مستقلة قبل رفع مستوى الثقة.",
        },
        {
            "id": "location_consistency",
            "label": "اتساق الموقع الحالي",
            "status": "not_available",
            "details": "بيانات الرقم الجغرافية لا تمثل موقع الجهاز الحالي.",
        },
    ]

    known = [
        "حالة صلاحية الرقم وفق metadata العامة.",
        "إمكانية الرقم من ناحية بنية الترقيم.",
        "نوع الرقم وبيانات الدولة المتاحة من metadata.",
        "المصادر والأدلة التي أعادها التحليل الفعلي.",
    ]
    if identity.get("status") in {"verified", "publicly_associated"}:
        known.append("توجد هوية مرتبطة بمصدر مصرح أو عام موثق.")
    if current_location.get("status") == "live":
        known.append("يوجد مصدر مصرح بموقع مباشر.")

    coverage_total = max(len(evidence_items) + 3, 1)
    coverage_percent = round((len(confirmed) + 0.5 * len(supported)) / coverage_total * 100)
    identity_confidence = "high" if identity.get("status") in {"verified_business", "verified_user_consent"} else (
        "medium" if identity.get("status") == "publicly_associated" else "unknown"
    )

    return {
        "executive_summary": {
            "headline": "تحليل ترقيم عام مع فصل الهوية والموقع عن الاستدلال.",
            "validity": "confirmed" if valid else "not_confirmed",
            "identity": identity_confidence,
            "live_location": "available" if current_location.get("status") == "live" else "unavailable",
            "evidence_coverage": coverage_percent,
        },
        "coverage": {
            "percent": coverage_percent,
            "confirmed": len(confirmed),
            "supported": len(supported),
            "unknown": len(unknowns),
            "method": "deterministic evidence weighting",
        },
        "confidence": {
            "overall": "high" if valid and len(confirmed) >= 3 else ("medium" if possible else "low"),
            "identity": identity_confidence,
            "reason": "الثقة مبنية على أدلة metadata المتاحة واتساقها؛ لا يتم احتساب التخمين كدليل.",
        },
        "source_registry": source_registry,
        "location_profile": location_profile or {},
        "consistency_checks": consistency_checks,
        "known": known,
        "unknown": unknowns,
        "timeline": [
            {"event": "lookup_started", "label": "بدء تحليل الرقم", "at": checked_at},
            {"event": "metadata_verified", "label": "تحليل metadata العامة", "at": checked_at},
            {"event": "identity_checked", "label": "فحص حالة الهوية", "at": checked_at},
            {"event": "location_checked", "label": "فحص مصدر الموقع المباشر", "at": checked_at},
        ],
        "identity_evidence_ledger": identity_evidence_ledger or [],
        "identity_provider_registry": identity_provider_registry or [],
        "social_summary": [
            {"id": app.get("id"), "name": app.get("name"), "verification": app.get("verification"), "status": app.get("status"), "source": app.get("source"), "checked_at": app.get("checked_at"), "evidence": app.get("evidence"), "method": app.get("method"), "note": app.get("note")}
            for app in social_apps
        ],
        "ai_analysis": {
            "status": "evidence_first",
            "provider": None,
            "model": None,
            "message": "محرك التحليل الحالي حتمي ومبني على الأدلة. لا يتم اختلاق نتائج بواسطة نموذج لغوي. يمكن إضافة مزود AI مصرح به لاحقًا فوق هذه الأدلة دون تغيير مصدر الحقيقة.",
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }
