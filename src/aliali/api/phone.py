import asyncio
import re

import phonenumbers
from phonenumbers import carrier, geocoder, number_type, timezone
from phonenumbers.phonenumberutil import NumberParseException

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


def _lookup_phone(value: str) -> dict[str, object]:
    cleaned = _clean(value)
    try:
        parsed = phonenumbers.parse(cleaned, None)
    except NumberParseException as exc:
        raise ValueError("تعذر فهم الرقم. استخدم الصيغة الدولية مع رمز الدولة.") from exc

    possible = phonenumbers.is_possible_number(parsed)
    valid = phonenumbers.is_valid_number(parsed)
    metadata_version = getattr(phonenumbers, "__version__", "unknown")
    base = {
        "ok": True,
        "type": "phone",
        "target": cleaned,
        "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        "country_code": parsed.country_code,
        "region_code": phonenumbers.region_code_for_number(parsed) or None,
        "valid": valid,
        "possible": possible,
        "line_type": _TYPE_NAMES.get(number_type(parsed), "غير معروف"),
        "carrier": carrier.name_for_number(parsed, "en") or None,
        "location": geocoder.description_for_number(parsed, "en") or None,
        "timezones": list(timezone.time_zones_for_number(parsed)),
        "source": "Google libphonenumber metadata",
        "evidence": {
            "source": "Google libphonenumber metadata",
            "metadata_version": metadata_version,
            "scope": "public numbering-plan metadata",
            "limitations": [
                "لا يثبت أن الرقم نشط حاليًا.",
                "معلومات شركة الاتصالات قد تمثل تخصيص النطاق الأصلي، لا المشغل الحالي.",
                "لا يتضمن اسم صاحب الرقم أو عنوانه أو حساباته الخاصة.",
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
        "national": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        "message": (
            "النتيجة مبنية على بيانات الترقيم العامة. اسم صاحب الرقم أو عنوانه أو حساباته "
            "لا يمكن استنتاجها من الرقم وحده."
        ),
    }


async def lookup_phone(value: str) -> dict[str, object]:
    return await asyncio.to_thread(_lookup_phone, value)
