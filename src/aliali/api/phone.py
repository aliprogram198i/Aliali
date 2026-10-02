import asyncio
import re
from datetime import UTC, datetime

import phonenumbers
from phonenumbers import carrier, geocoder, number_type, timezone
from phonenumbers.phonenumberutil import NumberParseException

from .intelligence import build_intelligence
from .social import check_social_presence

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_PHONE_RE = re.compile(r"^[+0-9().\-\s]{6,32}$")
_TYPE_NAMES = {
    phonenumbers.PhoneNumberType.FIXED_LINE: "خط ثابت",
    phonenumbers.PhoneNumberType.MOBILE: "هاتف محمول",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "ثابت أو محمول",
    phonenumbers.PhoneNumberType.TOLL_FREE: "رقم مجاني",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "خدمة مدفوعة",
    phonenumbers.PhoneNumberType.SHARED_COST: "تكلفة مشتركة",
    phonenumbers.PhoneNumberType.VOIP: "VoIP",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "رقم شخصي",
    phonenumbers.PhoneNumberType.PAGER: "Pager",
    phonenumbers.PhoneNumberType.UAN: "UAN",
    phonenumbers.PhoneNumberType.VOICEMAIL: "بريد صوتي",
    phonenumbers.PhoneNumberType.UNKNOWN: "غير معروف",
}


def _clean(value: str) -> str:
    cleaned = value.strip().translate(_ARABIC_DIGITS)
    if not _PHONE_RE.fullmatch(cleaned):
        raise ValueError("أدخل رقم هاتف صالحًا، ويفضل بالصيغة الدولية مثل +33123456789.")
    if not any(char.isdigit() for char in cleaned):
        raise ValueError("أدخل رقم هاتف صالحًا.")
    return cleaned


def _evidence_item(field: str, value: object, confidence: str, note: str | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "field": field,
        "value": value,
        "source": "Google libphonenumber metadata",
        "confidence": confidence,
        "kind": "public_metadata",
    }
    if note:
        item["note"] = note
    return item


def _lookup_phone(value: str) -> dict[str, object]:
    cleaned = _clean(value)
    try:
        parsed = phonenumbers.parse(cleaned, None)
    except NumberParseException as exc:
        raise ValueError("تعذر فهم الرقم. استخدم الصيغة الدولية مع رمز الدولة.") from exc

    possible = phonenumbers.is_possible_number(parsed)
    valid = phonenumbers.is_valid_number(parsed)
    metadata_version = getattr(phonenumbers, "__version__", "unknown")
    international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
    line_type = _TYPE_NAMES.get(number_type(parsed), "غير معروف")
    region_code = phonenumbers.region_code_for_number(parsed) or None
    carrier_name = carrier.name_for_number(parsed, "en") or None
    location = geocoder.description_for_number(parsed, "en") or None
    country_name = geocoder.country_name_for_number(parsed, "en") or None
    timezones = list(timezone.time_zones_for_number(parsed))

    evidence_items = [
        _evidence_item("validity", "valid" if valid else "not_valid", "high"),
        _evidence_item("possibility", "possible" if possible else "not_possible", "high"),
        _evidence_item("number_type", line_type, "high" if line_type != "غير معروف" else "low"),
        _evidence_item("country", country_name or region_code, "high"),
    ]
    if location:
        evidence_items.append(
            _evidence_item(
                "geographic_area",
                location,
                "medium",
                "منطقة مرتبطة ببيانات الرقم وليست موقعًا حاليًا للجهاز.",
            )
        )
    if carrier_name:
        evidence_items.append(
            _evidence_item(
                "carrier",
                carrier_name,
                "medium",
                "قد تمثل المعلومة تخصيص النطاق الأصلي ولا تعكس النقل بين المشغلين.",
            )
        )
    if timezones:
        evidence_items.append(
            _evidence_item(
                "timezones",
                timezones,
                "medium",
                "مناطق زمنية محتملة مرتبطة بالرقم، وليست موقعًا حاليًا.",
            )
        )

    identity = {
        "status": "not_established",
        "name": None,
        "source": None,
        "verified_at": None,
        "note": "لا توجد هوية شخصية موثقة في مصدر عام أو مصرح به ضمن هذا البحث.",
    }
    current_location = {
        "status": "not_available",
        "latitude": None,
        "longitude": None,
        "accuracy_m": None,
        "updated_at": None,
        "source": None,
        "note": "الموقع الحالي للجهاز لا يمكن استخراجه من رقم الهاتف وحده.",
    }

    checked_at = datetime.now(UTC).isoformat()
    source_name = "Google libphonenumber metadata"
    social_apps = check_social_presence()

    intelligence = build_intelligence(
        checked_at=checked_at,
        valid=valid,
        possible=possible,
        identity=identity,
        current_location=current_location,
        social_apps=social_apps,
        evidence_items=evidence_items,
        source=source_name,
        metadata_version=metadata_version,
    )

    base: dict[str, object] = {
        "ok": True,
        "type": "phone",
        "target": cleaned,
        "international": international,
        "e164": e164,
        "national": national,
        "country_code": parsed.country_code,
        "region_code": region_code,
        "country_name": country_name or None,
        "valid": valid,
        "possible": possible,
        "line_type": line_type,
        "carrier": carrier_name,
        "location": location,
        "timezones": timezones,
        "source": source_name,
        "checked_at": checked_at,
        "identity": identity,
        "current_location": current_location,
        "social_apps": social_apps,
        "analysis": {
            "status": "verified_public_metadata" if valid else "partial_public_metadata",
            "overall_confidence": "high" if valid else "medium",
            "evidence_count": len(evidence_items),
            "intelligence_version": "1.0",
        },
        **intelligence,
        "evidence": {
            "source": "Google libphonenumber metadata",
            "metadata_version": metadata_version,
            "scope": "public numbering-plan metadata",
            "items": evidence_items,
            "limitations": [
                "لا يثبت أن الرقم نشط حاليًا.",
                "معلومات شركة الاتصالات قد تمثل تخصيص النطاق الأصلي، لا المشغل الحالي.",
                "الموقع والمنطقة الزمنية إشارات مرتبطة ببيانات الرقم وليست تحديدًا لموقع الجهاز.",
                "لا يتضمن اسم صاحب الرقم أو عنوانه أو حساباته الخاصة أو موقع الجهاز الحالي.",
                "نتائج التواصل لا تُعد إثباتًا للحساب ما لم يرد دليل من مزود مصرح أو ارتباط عام موثق.",
            ],
        },
    }

    if not possible:
        raise ValueError("الرقم غير صالح من ناحية البنية.")

    if not valid:
        return {
            **base,
            "message": "تم التعرف على بنية الرقم، لكنه لا يطابق رقمًا صالحًا وفق بيانات الترقيم الحالية.",
        }

    return {
        **base,
        "message": (
            "النتيجة مبنية على بيانات الترقيم العامة. لا يمكن استنتاج هوية صاحب الرقم "
            "أو موقع الجهاز الحالي أو نشاطه من الرقم وحده."
        ),
    }


async def lookup_phone(value: str) -> dict[str, object]:
    return await asyncio.to_thread(_lookup_phone, value)
