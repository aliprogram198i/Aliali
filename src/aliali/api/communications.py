from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import threading
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from html import escape

from fastapi import HTTPException

try:
    from twilio.jwt.access_token import AccessToken
    from twilio.jwt.access_token.grants import VoiceGrant
except ImportError:  # pragma: no cover
    AccessToken = None
    VoiceGrant = None


class CommunicationError(RuntimeError):
    pass


class LocationStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS location_requests (
                    request_id TEXT PRIMARY KEY,
                    token_hash TEXT NOT NULL UNIQUE,
                    owner_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT,
                    latitude REAL,
                    longitude REAL,
                    accuracy_m REAL,
                    located_at TEXT
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_location_owner ON location_requests(owner_id)"
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, owner_id: object, ttl_seconds: int = 900) -> tuple[str, str, str]:
        request_id = f"loc-{uuid.uuid4().hex}"
        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=ttl_seconds)
        with self._lock, self._connect() as db:
            db.execute(
                """
                INSERT INTO location_requests
                (request_id, token_hash, owner_id, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    self._hash(token),
                    str(owner_id),
                    now.isoformat(),
                    expires.isoformat(),
                ),
            )
        return request_id, token, expires.isoformat()

    def submit(
        self,
        token: str,
        latitude: float,
        longitude: float,
        accuracy_m: float | None,
    ) -> bool:
        now = datetime.now(UTC)
        with self._lock, self._connect() as db:
            row = db.execute(
                "SELECT expires_at, consumed_at FROM location_requests WHERE token_hash = ?",
                (self._hash(token),),
            ).fetchone()
            if not row or row["consumed_at"]:
                return False
            if datetime.fromisoformat(row["expires_at"]) <= now:
                return False
            db.execute(
                """
                UPDATE location_requests
                SET consumed_at = ?, latitude = ?, longitude = ?, accuracy_m = ?, located_at = ?
                WHERE token_hash = ?
                """,
                (
                    now.isoformat(),
                    latitude,
                    longitude,
                    accuracy_m,
                    now.isoformat(),
                    self._hash(token),
                ),
            )
        return True

    def get(self, request_id: str, owner_id: object) -> dict[str, object] | None:
        with self._lock, self._connect() as db:
            row = db.execute(
                "SELECT * FROM location_requests WHERE request_id = ? AND owner_id = ?",
                (request_id, str(owner_id)),
            ).fetchone()
        if not row:
            return None
        expired = datetime.fromisoformat(row["expires_at"]) <= datetime.now(UTC)
        return {
            "request_id": row["request_id"],
            "status": "expired" if expired and not row["located_at"] else (
                "located" if row["located_at"] else "pending"
            ),
            "expires_at": row["expires_at"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "accuracy_m": row["accuracy_m"],
            "located_at": row["located_at"],
        }


def _twilio_request(
    *,
    account_sid: str,
    auth_token: str,
    resource: str,
    values: dict[str, str],
) -> dict[str, object]:
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/{resource}.json"
    body = urllib.parse.urlencode(values).encode("utf-8")
    password = auth_token.encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    credentials = f"{account_sid}:{auth_token}".encode("utf-8")
    import base64

    request.add_header(
        "Authorization",
        "Basic " + base64.b64encode(credentials).decode("ascii"),
    )
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            import json

            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise CommunicationError("تعذر الوصول إلى مزود الاتصالات.") from exc


def send_sms(
    *,
    account_sid: str | None,
    auth_token: str | None,
    from_number: str | None,
    to_number: str,
    body: str,
) -> str:
    if not account_sid or not auth_token or not from_number:
        raise CommunicationError("خدمة SMS غير مهيأة في الخادم.")
    result = _twilio_request(
        account_sid=account_sid,
        auth_token=auth_token,
        resource="Messages",
        values={"From": from_number, "To": to_number, "Body": body},
    )
    sid = result.get("sid")
    if not isinstance(sid, str):
        raise CommunicationError("مزود SMS لم يُرجع معرف الرسالة.")
    return sid


def create_voice_token(
    *,
    account_sid: str | None,
    api_key_sid: str | None,
    api_key_secret: str | None,
    twiml_app_sid: str | None,
    identity: str,
) -> str:
    if not all((account_sid, api_key_sid, api_key_secret, twiml_app_sid)):
        raise CommunicationError("خدمة الاتصال داخل التطبيق غير مهيأة في الخادم.")
    if AccessToken is None or VoiceGrant is None:
        raise CommunicationError("مكتبة الاتصال غير متاحة في الخادم.")
    safe_identity = "u_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    token = AccessToken(
        account_sid,
        api_key_sid,
        api_key_secret,
        identity=safe_identity,
        ttl=900,
    )
    token.add_grant(VoiceGrant(outgoing_application_sid=twiml_app_sid))
    value = token.to_jwt()
    return value.decode("utf-8") if isinstance(value, bytes) else value


def validate_twilio_signature(
    *,
    auth_token: str,
    url: str,
    params: dict[str, str],
    signature: str | None,
) -> bool:
    if not signature:
        return False
    data = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    expected = hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()
    import base64

    return hmac.compare_digest(base64.b64encode(expected).decode("ascii"), signature)


def build_location_page(token: str) -> str:
    safe_token = escape(token, quote=True)
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>مشاركة الموقع · Aliali</title>
<style>
body{{margin:0;background:#07111f;color:#eef4ff;font-family:system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;padding:20px}}
main{{width:min(460px,100%);padding:24px;border:1px solid #29405a;border-radius:22px;background:#0a1726;box-sizing:border-box}}
h1{{font-size:23px;margin:0 0 10px}}p{{color:#9db0ca;line-height:1.7;font-size:14px}}
button{{width:100%;padding:14px;border:1px solid #4776a7;border-radius:12px;background:#163554;color:white;font-weight:800;font-size:15px}}
.status{{margin-top:14px;padding:12px;border-radius:12px;background:#101d2c;color:#b9c9da;font-size:13px}}
.small{{font-size:11px;color:#70869f}}
</style></head>
<body><main>
<h1>📍 طلب مشاركة الموقع</h1>
<p>إذا كنت موافقًا، اضغط الزر للسماح للمتصفح بطلب موقع جهازك. لن يتم إرسال الموقع قبل موافقتك.</p>
<button id="share">مشاركة موقعي</button>
<div id="status" class="status">بانتظار موافقتك.</div>
<p class="small">الرابط مؤقت ويُستخدم مرة واحدة.</p>
<script>
const token = "{safe_token}";
const statusEl = document.getElementById("status");
document.getElementById("share").addEventListener("click", () => {{
  if (!navigator.geolocation) {{
    statusEl.textContent = "هذا المتصفح لا يدعم تحديد الموقع.";
    return;
  }}
  statusEl.textContent = "جاري طلب إذن الموقع…";
  navigator.geolocation.getCurrentPosition(async (position) => {{
    statusEl.textContent = "جاري إرسال الموقع بشكل آمن…";
    try {{
      const response = await fetch("/api/v1/location/" + encodeURIComponent(token), {{
        method: "POST",
        headers: {{"Content-Type":"application/json"}},
        body: JSON.stringify({{
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy_m: position.coords.accuracy
        }})
      }});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "تعذر إرسال الموقع.");
      statusEl.textContent = "✓ تم إرسال الموقع بنجاح. يمكنك إغلاق هذه الصفحة.";
      document.getElementById("share").disabled = true;
    }} catch (error) {{
      statusEl.textContent = error instanceof Error ? error.message : "تعذر إرسال الموقع.";
    }}
  }}, (error) => {{
    statusEl.textContent = error.code === 1 ? "تم رفض إذن الموقع." : "تعذر الحصول على الموقع.";
  }}, {{enableHighAccuracy:true, timeout:15000, maximumAge:0}});
}});
</script></main></body></html>"""


def validate_coordinates(latitude: float, longitude: float, accuracy_m: float | None) -> None:
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(status_code=422, detail="إحداثيات الموقع غير صالحة.")
    if accuracy_m is not None and (accuracy_m < 0 or accuracy_m > 100000):
        raise HTTPException(status_code=422, detail="دقة الموقع غير صالحة.")
