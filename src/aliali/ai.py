from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class AIConfigurationError(RuntimeError):
    pass


class AIProviderError(RuntimeError):
    pass


def analyze_evidence(
    *,
    evidence: dict[str, Any],
    api_key: str | None,
    model: str,
    enabled: bool,
    timeout_seconds: float = 12.0,
) -> dict[str, Any]:
    """Analyze collected evidence; never use AI as a source of identity facts."""
    if not enabled:
        return {
            "status": "disabled",
            "provider": None,
            "model": None,
            "message": "تحليل AI الخارجي غير مفعّل. النتيجة الأساسية تبقى مبنية على الأدلة المحلية.",
        }
    if not api_key:
        raise AIConfigurationError("OPENAI_API_KEY غير مضبوط.")

    safe_payload = {
        "number_type": evidence.get("line_type"),
        "country": evidence.get("country_name"),
        "region": evidence.get("region_code"),
        "carrier": evidence.get("carrier"),
        "geographic_area": evidence.get("location"),
        "timezones": evidence.get("timezones"),
        "valid": evidence.get("valid"),
        "possible": evidence.get("possible"),
        "evidence": [
            {
                "field": item.get("field"),
                "value": item.get("value"),
                "confidence": item.get("confidence"),
                "kind": item.get("kind"),
            }
            for item in evidence.get("evidence", {}).get("items", [])
        ],
    }

    instructions = (
        "أنت محلل أدلة هاتفية. حلل الأدلة المقدمة فقط. لا تستنتج اسم شخص أو موقع جهاز "
        "أو ملكية رقم أو حساب اجتماعي. لا تعتبر التخمين دليلاً. أعد JSON صالحاً يحتوي على "
        "summary_ar و findings_ar و contradictions_ar و limitations_ar و confidence_reason_ar. "
        "إذا لم توجد أدلة كافية فقل ذلك صراحة."
    )
    body = {
        "model": model,
        "store": False,
        "input": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(safe_payload, ensure_ascii=False)},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "phone_evidence_analysis",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "summary_ar": {"type": "string"},
                        "findings_ar": {"type": "array", "items": {"type": "string"}},
                        "contradictions_ar": {"type": "array", "items": {"type": "string"}},
                        "limitations_ar": {"type": "array", "items": {"type": "string"}},
                        "confidence_reason_ar": {"type": "string"},
                    },
                    "required": [
                        "summary_ar",
                        "findings_ar",
                        "contradictions_ar",
                        "limitations_ar",
                        "confidence_reason_ar",
                    ],
                },
            }
        },
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AIProviderError("تعذر الوصول إلى مزود AI.") from exc

    output_text = raw.get("output_text")
    if not isinstance(output_text, str):
        for item in raw.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                    output_text = content["text"]
                    break
            if output_text:
                break
    if not isinstance(output_text, str):
        raise AIProviderError("مزود AI أعاد استجابة بلا تحليل نصي.")

    try:
        analysis = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise AIProviderError("استجابة AI ليست JSON صالحًا.") from exc

    return {
        "status": "completed",
        "provider": "openai",
        "model": model,
        "analysis": analysis,
        "message": "تم تحليل الأدلة المحلية فقط؛ لم تُرسل الهوية الشخصية أو رقم الهاتف الخام إلى مزود AI.",
    }
