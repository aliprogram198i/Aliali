from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib import error, request

from .config import Settings

_OPENAI_URL = "https://api.openai.com/v1/responses"

_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "evidence_interpretation": {"type": "string"},
        "cautions": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "evidence_interpretation", "cautions", "next_steps"],
    "additionalProperties": False,
}


def _sanitize_evidence(result: dict[str, Any]) -> dict[str, Any]:
    evidence = result.get("evidence") or {}
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
                "field": item.get("field"),
                "value": item.get("value"),
                "confidence": item.get("confidence"),
                "note": item.get("note"),
            }
            for item in evidence.get("items", [])
        ],
        "limitations": evidence.get("limitations") or [],
    }


def build_ai_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Return only non-identifying evidence; never include the searched number."""
    return {
        "task": "Analyze public phone-number metadata only. Do not infer a person, account, address, or live location.",
        "evidence": _sanitize_evidence(result),
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


async def analyze_with_openai(result: dict[str, Any], settings: Settings) -> dict[str, Any]:
    if not settings.ai_enabled:
        return {"status": "disabled", "provider": None, "model": None, "message": "التحليل الذكي معطل افتراضيًا."}
    if not settings.openai_api_key:
        return {"status": "not_configured", "provider": None, "model": settings.openai_model, "message": "مزود AI غير مُهيأ؛ تم الاحتفاظ بالتحليل الحتمي كمصدر الحقيقة."}

    payload = {
        "model": settings.openai_model,
        "store": False,
        "input": [
            {"role": "system", "content": "You are an evidence analyst. Analyze only supplied public metadata. Never infer identity, private accounts, address, or live device location. State uncertainty explicitly and do not invent missing facts."},
            {"role": "user", "content": json.dumps(build_ai_payload(result), ensure_ascii=False)},
        ],
        "text": {"format": {"type": "json_schema", "name": "phone_evidence_analysis", "strict": True, "schema": _SCHEMA}},
    }
    req = request.Request(
        _OPENAI_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = await asyncio.to_thread(request.urlopen, req, timeout=20)
        with response:
            raw = response.read().decode("utf-8")
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        return {"status": "provider_error", "provider": "openai", "model": settings.openai_model, "message": "تعذر الوصول إلى مزود AI؛ بقيت النتيجة الحتمية هي مصدر الحقيقة.", "error_type": type(exc).__name__}

    try:
        response_payload = json.loads(raw)
        analysis = json.loads(_extract_output_text(response_payload))
        if not isinstance(analysis, dict):
            raise TypeError("AI output is not an object")
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        return {"status": "invalid_provider_output", "provider": "openai", "model": settings.openai_model, "message": "أعاد مزود AI مخرجات غير صالحة؛ لم يتم اعتمادها.", "error_type": type(exc).__name__}

    return {"status": "completed", "provider": "openai", "model": settings.openai_model, "message": "تم تحليل الأدلة العامة فقط؛ هذه الطبقة لا تُنشئ حقائق هوية أو موقع.", "analysis": analysis}
