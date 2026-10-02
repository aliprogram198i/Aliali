from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib import error, request

from .config import Settings

AI_POLICY_VERSION = "3.0"
EVIDENCE_SCHEMA_VERSION = "2.0"
ANALYSIS_VERSION = "2.0"
SNAPSHOT_TTL_SECONDS = 900
_OPENAI_URL = "https://api.openai.com/v1/responses"

_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "evidence_interpretation": {"type": "string"},
        "cautions": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "array", "items": {"type": "string"}},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "support": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low", "unknown"]},
                },
                "required": ["claim", "support", "confidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "evidence_interpretation", "cautions", "next_steps", "claims"],
    "additionalProperties": False,
}


def _sanitize_evidence(result: dict[str, Any]) -> dict[str, Any]:
    evidence = result.get("evidence") or {}
    intelligence = {
        "confidence": result.get("confidence"),
        "consistency_checks": result.get("consistency_checks") or [],
        "coverage": result.get("coverage"),
        "unknown": result.get("unknown") or [],
    }
    return {
        "valid": result.get("valid"),
        "possible": result.get("possible"),
        "country": result.get("country_name") or result.get("region_code"),
        "country_code": result.get("country_code"),
        "region_code": result.get("region_code"),
        "line_type": result.get("line_type"),
        "carrier": result.get("carrier"),
        "geographic_area": result.get("location"),
        "timezones": result.get("timezones") or [],
        "evidence_items": [
            {
                "id": f"E{index + 1}",
                "field": item.get("field"),
                "value": item.get("value"),
                "confidence": item.get("confidence"),
                "note": item.get("note"),
                "kind": item.get("kind"),
            }
            for index, item in enumerate(evidence.get("items", []))
        ],
        "social_summary": [
            {
                "id": item.get("id"),
                "status": item.get("status"),
                "verification": item.get("verification"),
                "source": item.get("source"),
                "method": item.get("method"),
            }
            for item in result.get("social_apps", [])
        ],
        "limitations": evidence.get("limitations") or [],
        "intelligence": intelligence,
    }


def build_ai_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Build an identifying-data-free, versioned AI evidence snapshot."""
    return {
        "policy_version": AI_POLICY_VERSION,
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "task": (
            "Analyze supplied evidence only. Never infer identity, private accounts, "
            "address, or live device location. Unknown means unknown."
        ),
        "evidence": _sanitize_evidence(result),
    }


def create_evidence_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    snapshot = build_ai_payload(result)
    return {
        "analysis_id": f"ali-{uuid.uuid4().hex}",
        "created_at": datetime.now(UTC).isoformat(),
        "payload": snapshot,
    }


def detect_conflicts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("evidence", {}).get("evidence_items", [])
    by_field: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_field.setdefault(str(item.get("field")), []).append(item)
    conflicts = []
    for field, values in by_field.items():
        normalized = {json.dumps(v.get("value"), sort_keys=True, ensure_ascii=False) for v in values}
        if len(normalized) > 1:
            conflicts.append({
                "field": field,
                "status": "unresolved",
                "evidence_ids": [v["id"] for v in values],
                "details": "Multiple evidence values disagree; no automatic winner is selected.",
            })
    return conflicts


def _deterministic_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = payload["evidence"]
    conflicts = detect_conflicts(payload)
    items = evidence["evidence_items"]
    high = [x for x in items if x.get("confidence") == "high"]
    medium = [x for x in items if x.get("confidence") == "medium"]
    unknown = evidence.get("unknown") or []
    return {
        "status": "deterministic_verified",
        "summary": (
            f"تم تحليل {len(items)} أدلة عامة؛ {len(high)} عالية الثقة و{len(medium)} متوسطة الثقة."
        ),
        "evidence_interpretation": (
            "التحليل يفصل metadata العامة عن الهوية والموقع الحالي. "
            + ("يوجد تعارض يحتاج مصدرًا مستقلًا." if conflicts else "لا يوجد تعارض مسجل بين الأدلة الحالية.")
        ),
        "cautions": list(evidence.get("limitations") or [])[:6],
        "next_steps": [
            "التحقق من أي مصدر مصرح قبل رفع مستوى الثقة.",
            "عدم تحويل المنطقة أو شركة الاتصالات إلى موقع حالي.",
            "إعادة الفحص فقط عند توفر دليل جديد.",
        ],
        "claims": [
            {
                "claim": f"{item.get('field')}: {item.get('value')}",
                "support": [item["id"]],
                "confidence": item.get("confidence", "unknown"),
            }
            for item in items
        ],
        "conflicts": conflicts,
        "unknown": unknown,
    }


def verify_analysis(analysis: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Independently validate AI output against the supplied evidence contract."""
    conflicts = detect_conflicts(payload)
    violations: list[str] = []
    evidence_ids = {
        str(item.get("id"))
        for item in payload.get("evidence", {}).get("evidence_items", [])
        if item.get("id")
    }
    forbidden_terms = (
        "owner", "identity", "address", "live location", "current location",
        "هوية", "صاحب الرقم", "عنوان", "موقع الجهاز الحالي", "الموقع الحالي",
    )
    allowed_confidence = {"high", "medium", "low", "unknown"}

    claims = analysis.get("claims", [])
    if not isinstance(claims, list):
        violations.append("claims_not_array")
        claims = []

    for claim in claims:
        if not isinstance(claim, dict):
            violations.append("invalid_claim")
            continue
        claim_text = str(claim.get("claim", "")).lower()
        support = claim.get("support")
        confidence = claim.get("confidence")
        if not isinstance(support, list):
            violations.append("claim_support_not_array")
            support = []
        if any(str(item) not in evidence_ids for item in support):
            violations.append("claim_support_not_in_evidence")
        if confidence not in allowed_confidence:
            violations.append("invalid_claim_confidence")
        if any(term in claim_text for term in forbidden_terms):
            violations.append("forbidden_sensitive_claim")

    # A conflict is never converted into a resolved fact by the verifier.
    if conflicts:
        violations.append("unresolved_evidence_conflict")

    verified = not violations
    unique_violations = list(dict.fromkeys(violations))
    return {
        "status": "passed" if verified else "rejected",
        "verified": verified,
        "violations": unique_violations,
        "conflicts": conflicts,
        "risk": "low" if verified else "high" if any(
            item in unique_violations
            for item in ("forbidden_sensitive_claim", "claim_support_not_in_evidence")
        ) else "medium",
        "message": "تم اجتياز فحص الأدلة والسياسة." if verified else "تم رفض مخرجات لا تطابق عقد الأدلة.",
    }


def build_audit_record(
    analysis: dict[str, Any],
    *,
    duration_ms: int,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Return non-sensitive operational metadata for an AI audit ledger."""
    verification = analysis.get("verification") or {}
    return {
        "analysis_id": analysis.get("analysis_id"),
        "recorded_at": recorded_at or datetime.now(UTC).isoformat(),
        "status": analysis.get("status"),
        "provider": analysis.get("provider"),
        "model": analysis.get("model"),
        "policy_version": analysis.get("policy_version", AI_POLICY_VERSION),
        "analysis_version": analysis.get("analysis_version", ANALYSIS_VERSION),
        "verification_status": verification.get("status"),
        "verification_risk": verification.get("risk"),
        "duration_ms": max(0, int(duration_ms)),
    }


def _extract_output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                return content["text"]
    raise ValueError("لم يُرجع مزود AI نصًا قابلاً للتحليل.")


async def analyze_with_openai(
    result: dict[str, Any],
    settings: Settings,
    *,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_snapshot = snapshot or create_evidence_snapshot(result)
    payload = evidence_snapshot["payload"]
    deterministic = _deterministic_analysis(payload)

    if not settings.ai_enabled:
        return {
            "status": "deterministic_only",
            "provider": None,
            "model": None,
            "analysis_id": evidence_snapshot["analysis_id"],
            "policy_version": AI_POLICY_VERSION,
            "analysis_version": ANALYSIS_VERSION,
            "verification": verify_analysis(deterministic, payload),
            "analysis": deterministic,
            "message": "تحليل الأدلة الحتمي هو مصدر الحقيقة؛ طبقة AI الخارجية معطلة.",
        }
    if not settings.openai_api_key:
        return {
            "status": "not_configured",
            "provider": None,
            "model": settings.openai_model,
            "analysis_id": evidence_snapshot["analysis_id"],
            "policy_version": AI_POLICY_VERSION,
            "analysis_version": ANALYSIS_VERSION,
            "verification": verify_analysis(deterministic, payload),
            "analysis": deterministic,
            "message": "مزود AI غير مهيأ؛ تم الاحتفاظ بالتحليل الحتمي كمصدر الحقيقة.",
        }

    prompt = {
        "policy": AI_POLICY_VERSION,
        "evidence_schema": EVIDENCE_SCHEMA_VERSION,
        "instruction": (
            "Act as an evidence analyst. Every claim must cite supplied evidence IDs. "
            "Never infer identity, private accounts, address, or live device location. "
            "If evidence is missing, say unknown. Do not resolve conflicts by guessing."
        ),
        "snapshot": payload,
    }
    api_payload = {
        "model": settings.openai_model,
        "store": False,
        "input": [
            {"role": "system", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "text": {"format": {"type": "json_schema", "name": "aliali_intelligence_analysis", "strict": True, "schema": _SCHEMA}},
    }
    req = request.Request(
        _OPENAI_URL,
        data=json.dumps(api_payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = await asyncio.to_thread(request.urlopen, req, timeout=20)
        with response:
            raw = response.read().decode("utf-8")
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        return {
            "status": "provider_error",
            "provider": "openai",
            "model": settings.openai_model,
            "analysis_id": evidence_snapshot["analysis_id"],
            "verification": verify_analysis(deterministic, payload),
            "analysis": deterministic,
            "message": "تعذر الوصول إلى مزود AI؛ تم استخدام التحليل الحتمي كبديل آمن.",
            "error_type": type(exc).__name__,
        }

    try:
        response_payload = json.loads(raw)
        analysis = json.loads(_extract_output_text(response_payload))
        if not isinstance(analysis, dict):
            raise TypeError("AI output is not an object")
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        return {
            "status": "invalid_provider_output",
            "provider": "openai",
            "model": settings.openai_model,
            "analysis_id": evidence_snapshot["analysis_id"],
            "verification": verify_analysis(deterministic, payload),
            "analysis": deterministic,
            "message": "أعاد مزود AI مخرجات غير صالحة؛ لم يتم اعتمادها.",
            "error_type": type(exc).__name__,
        }

    verification = verify_analysis(analysis, payload)
    if verification["verified"]:
        final_analysis = analysis
        status = "completed_verified"
        message = "تم تحليل الأدلة ثم اجتياز طبقة التحقق المستقلة."
    else:
        final_analysis = deterministic
        status = "completed_fallback"
        message = "تم رفض مخرجات AI غير المدعومة؛ عادت النتيجة إلى التحليل الحتمي."

    return {
        "status": status,
        "provider": "openai",
        "model": settings.openai_model,
        "analysis_id": evidence_snapshot["analysis_id"],
        "policy_version": AI_POLICY_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "verification": verification,
        "analysis": final_analysis,
        "message": message,
    }
