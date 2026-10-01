import asyncio
import ipaddress
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

_MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


def _normalize_mac(value: str) -> str:
    normalized = value.strip().upper().replace("-", ":")
    if not _MAC_RE.fullmatch(normalized):
        raise ValueError("أدخل عنوان MAC صحيحًا.")
    return normalized


def _fetch_json(url: str) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "Aliali-Network-Lookup/1.0"})
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise LookupError("تعذر الوصول إلى خدمة البحث على الإنترنت.") from exc
    if not isinstance(payload, dict):
        raise LookupError("خدمة البحث أعادت استجابة غير صالحة.")
    return payload


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Aliali-Network-Lookup/1.0"})
    try:
        with urlopen(request, timeout=8) as response:
            return response.read().decode("utf-8").strip()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise LookupError("تعذر الوصول إلى خدمة تعريف الشركة المصنّعة.") from exc


def _lookup_ip(ip: str) -> dict[str, object]:
    address = ipaddress.ip_address(ip.strip())
    base = {
        "type": "ip",
        "target": str(address),
        "ip_version": f"IPv{address.version}",
        "scope": "Public" if address.is_global else "Private/Local",
    }

    if not address.is_global:
        return {
            "ok": True,
            **base,
            "name": "عنوان IP خاص/محلي",
            "organization": None,
            "isp": None,
            "asn": None,
            "domain": None,
            "location": None,
            "country": None,
            "region": None,
            "city": None,
            "latitude": None,
            "longitude": None,
            "timezone": None,
            "is_eu": None,
            "message": "هذا عنوان خاص ولا يمكن ربطه باسم شبكة على الإنترنت العام. يلزم عنوان IP عام لإجراء البحث.",
            "source": "Local address classification",
        }

    payload = _fetch_json(f"https://ipwho.is/{quote(str(address), safe='')}")
    if payload.get("success") is not True:
        raise LookupError(str(payload.get("message") or "لم يتم العثور على معلومات عن عنوان IP."))

    connection = payload.get("connection")
    if not isinstance(connection, dict):
        connection = {}
    timezone = payload.get("timezone")
    if not isinstance(timezone, dict):
        timezone = {}

    organization = connection.get("org") or connection.get("isp")
    isp = connection.get("isp")
    location_parts = [
        part for part in (payload.get("city"), payload.get("region"), payload.get("country"))
        if isinstance(part, str) and part
    ]

    return {
        "ok": True,
        **base,
        "name": organization or isp or "شبكة غير معروفة",
        "organization": organization,
        "isp": isp,
        "asn": connection.get("asn"),
        "domain": connection.get("domain"),
        "location": ", ".join(location_parts) or None,
        "country": payload.get("country"),
        "country_code": payload.get("country_code"),
        "region": payload.get("region"),
        "city": payload.get("city"),
        "continent": payload.get("continent"),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "timezone": timezone.get("id") or timezone.get("utc"),
        "is_eu": payload.get("is_eu"),
        "message": "تم العثور على معلومات الشبكة من مصدر إنترنت عام. الموقع جغرافي تقريبي.",
        "source": "ipwho.is",
    }


def _mac_assignment(mac: str) -> str:
    first_octet = int(mac.split(":")[0], 16)
    if first_octet & 0x01:
        return "Multicast"
    if first_octet & 0x02:
        return "Locally administered"
    return "Globally administered"


def _lookup_mac(mac: str) -> dict[str, object]:
    normalized = _normalize_mac(mac)
    vendor = _fetch_text(f"https://api.macvendors.com/{quote(normalized, safe='')}")
    vendor = vendor or "غير معروف"
    return {
        "ok": True,
        "type": "mac",
        "target": normalized,
        "name": vendor,
        "organization": vendor if vendor != "غير معروف" else None,
        "isp": None,
        "asn": None,
        "domain": None,
        "location": None,
        "oui": normalized[:8],
        "assignment": _mac_assignment(normalized),
        "message": "تم تعريف الشركة المصنّعة من OUI. عنوان MAC لا يحدد اسم شبكة عامة أو موقع الجهاز على الإنترنت.",
        "source": "macvendors.com",
    }


def _detect_target(value: str) -> tuple[str, str]:
    target = value.strip()
    if not target:
        raise ValueError("أدخل عنوان IP أو MAC.")
    try:
        return "ip", str(ipaddress.ip_address(target))
    except ValueError:
        return "mac", _normalize_mac(target)


async def lookup_target(value: str) -> dict[str, object]:
    kind, target = _detect_target(value)
    if kind == "ip":
        return await asyncio.to_thread(_lookup_ip, target)
    return await asyncio.to_thread(_lookup_mac, target)
