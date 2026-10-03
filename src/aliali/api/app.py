import urllib.parse
from collections import defaultdict, deque
from datetime import UTC, datetime
from time import monotonic

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from ..ai import (
    SNAPSHOT_TTL_SECONDS,
    analyze_with_openai,
    build_audit_record,
    create_evidence_snapshot,
)
from ..config import Settings
from ..core.errors import SecurityError
from .auth import create_session_token, validate_session_token, validate_telegram_init_data
from .communications import (
    CommunicationAuthorizationStore,
    CommunicationError,
    LocationStore,
    build_location_page,
    create_voice_token,
    normalize_e164,
    send_sms,
    validate_coordinates,
    validate_twilio_signature,
)
from .phone import lookup_phone


class SessionRequest(BaseModel):
    init_data: str


class LookupRequest(SessionRequest):
    target: str


class AIAnalysisRequest(SessionRequest):
    analysis_id: str


class CommunicationRequest(SessionRequest):
    analysis_id: str


class LocationRequest(SessionRequest):
    analysis_id: str


class LocationPayload(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: float | None = None


def _authenticate(init_data: str, settings: Settings) -> dict[str, object]:
    try:
        return validate_telegram_init_data(init_data, settings.bot_token)
    except SecurityError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title="Aliali Reverse Phone Lookup", version="2.1.0")

    origins = [resolved_settings.mini_app_url] if resolved_settings.mini_app_url else []
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["POST", "GET"],
            allow_headers=["Content-Type", "X-Telegram-Init-Data", "X-Aliali-Session"],
        )

    # Process-local guardrail. It intentionally does not persist phone numbers or query targets.
    request_windows: dict[str, deque[float]] = defaultdict(deque)
    ai_request_windows: dict[str, deque[float]] = defaultdict(deque)
    evidence_snapshots: dict[str, dict[str, object]] = {}
    audit_ledger: dict[str, deque[dict[str, object]]] = defaultdict(lambda: deque(maxlen=100))
    location_store = LocationStore(resolved_settings.location_db_path)
    communication_auth_store = CommunicationAuthorizationStore(resolved_settings.location_db_path)
    communication_windows: dict[str, deque[float]] = defaultdict(deque)
    rate_limit = 20
    ai_rate_limit = 6
    window_seconds = 60.0
    max_snapshots = 500
    max_snapshots_per_user = 20
    communication_rate_limit = 5

    def authenticate_request(init_data: str, session_token: str | None) -> dict[str, object]:
        if session_token:
            try:
                session = validate_session_token(session_token, resolved_settings.bot_token)
                return {"user": {"id": session["user_id"]}, "auth_date": None}
            except SecurityError:
                pass
        return _authenticate(init_data, resolved_settings)

    def purge_expired_snapshots() -> None:
        now = datetime.now(UTC)
        expired: list[str] = []
        for analysis_id, snapshot in evidence_snapshots.items():
            created_at = snapshot.get("created_at")
            if not isinstance(created_at, str):
                expired.append(analysis_id)
                continue
            try:
                created = datetime.fromisoformat(created_at)
            except ValueError:
                expired.append(analysis_id)
                continue
            if (now - created).total_seconds() >= SNAPSHOT_TTL_SECONDS:
                expired.append(analysis_id)
        for analysis_id in expired:
            evidence_snapshots.pop(analysis_id, None)

    def enforce_ai_rate_limit(user_id: object) -> None:
        now = monotonic()
        key = str(user_id)
        window = ai_request_windows[key]
        while window and now - window[0] >= window_seconds:
            window.popleft()
        if len(window) >= ai_rate_limit:
            raise HTTPException(
                status_code=429,
                detail="تم تجاوز حد التحليل الذكي المؤقت. حاول مرة أخرى بعد قليل.",
                headers={"Retry-After": str(int(window_seconds))},
            )
        window.append(now)

    def enforce_snapshot_quota(user_id: object) -> None:
        user_snapshots = [
            (analysis_id, snapshot)
            for analysis_id, snapshot in evidence_snapshots.items()
            if snapshot.get("owner_id") == user_id
        ]
        if len(user_snapshots) >= max_snapshots_per_user:
            evidence_snapshots.pop(user_snapshots[0][0], None)

    def enforce_communication_rate_limit(user_id: object) -> None:
        now = monotonic()
        key = str(user_id)
        window = communication_windows[key]
        while window and now - window[0] >= window_seconds:
            window.popleft()
        if len(window) >= communication_rate_limit:
            raise HTTPException(
                status_code=429,
                detail="تم تجاوز حد الاتصالات المؤقت. حاول مرة أخرى بعد قليل.",
                headers={"Retry-After": str(int(window_seconds))},
            )
        window.append(now)

    def enforce_rate_limit(user_id: object) -> None:
        now = monotonic()
        key = str(user_id)
        window = request_windows[key]
        while window and now - window[0] >= window_seconds:
            window.popleft()
        if len(window) >= rate_limit:
            raise HTTPException(
                status_code=429,
                detail="تم تجاوز حد البحث المؤقت. حاول مرة أخرى بعد قليل.",
                headers={"Retry-After": str(int(window_seconds))},
            )
        window.append(now)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/session")
    async def create_session(
        request: SessionRequest,
        x_telegram_init_data: str | None = Header(default=None),
        x_aliali_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        identity = authenticate_request(init_data, x_aliali_session)
        return {
            "authenticated": True,
            "user": identity["user"],
            "auth_date": identity["auth_date"],
            "session_token": create_session_token(identity, resolved_settings.bot_token),
            "session_ttl_seconds": 21600,
        }

    @app.post("/api/v1/ai-analysis")
    async def ai_analysis(
        request: AIAnalysisRequest,
        x_telegram_init_data: str | None = Header(default=None),
        x_aliali_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        identity = authenticate_request(init_data, x_aliali_session)
        user = identity.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id is None:
            raise HTTPException(status_code=401, detail="تعذر تحديد هوية مستخدم Telegram.")
        enforce_ai_rate_limit(user_id)
        purge_expired_snapshots()
        snapshot = evidence_snapshots.get(request.analysis_id)
        if not snapshot or snapshot.get("owner_id") != user_id:
            raise HTTPException(status_code=404, detail="لقطة الأدلة غير متاحة لهذه الجلسة.")
        started = monotonic()
        result = await analyze_with_openai({}, resolved_settings, snapshot=snapshot)
        audit_ledger[str(user_id)].append(
            build_audit_record(
                result,
                duration_ms=int((monotonic() - started) * 1000),
            )
        )
        return result

    @app.post("/api/v1/ai-audit")
    async def ai_audit(
        request: SessionRequest,
        x_telegram_init_data: str | None = Header(default=None),
        x_aliali_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        effective_init_data = x_telegram_init_data or request.init_data
        identity = authenticate_request(effective_init_data, x_aliali_session)
        user = identity.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id is None:
            raise HTTPException(status_code=401, detail="تعذر تحديد هوية مستخدم Telegram.")
        return {"items": list(audit_ledger.get(str(user_id), ()))}

    @app.post("/api/v1/voice/token")
    async def voice_token(
        request: SessionRequest,
        x_telegram_init_data: str | None = Header(default=None),
        x_aliali_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        identity = authenticate_request(init_data, x_aliali_session)
        user = identity.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id is None:
            raise HTTPException(status_code=401, detail="تعذر تحديد هوية مستخدم Telegram.")
        enforce_communication_rate_limit(user_id)
        snapshot = evidence_snapshots.get(request.analysis_id)
        if not snapshot or snapshot.get("owner_id") != user_id or not snapshot.get("target_e164"):
            raise HTTPException(status_code=404, detail="نتيجة البحث غير متاحة لهذه الجلسة.")
        target_e164 = str(snapshot["target_e164"])
        authorization = communication_auth_store.create(user_id, target_e164, ttl_seconds=300)
        try:
            token = create_voice_token(
                account_sid=resolved_settings.twilio_account_sid,
                api_key_sid=resolved_settings.twilio_api_key_sid,
                api_key_secret=resolved_settings.twilio_api_key_secret,
                twiml_app_sid=resolved_settings.twilio_voice_app_sid,
                identity=str(user_id),
            )
        except CommunicationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"token": token, "authorization": authorization, "ttl_seconds": 900}

    @app.post("/api/v1/voice/twiml")
    async def voice_twiml(request: Request) -> Response:
        raw = await request.body()
        params = {key: values[-1] for key, values in urllib.parse.parse_qs(raw.decode()).items() if values}
        signature = request.headers.get("X-Twilio-Signature")
        if not resolved_settings.twilio_auth_token or not validate_twilio_signature(
            auth_token=resolved_settings.twilio_auth_token,
            url=str(request.url),
            params=params,
            signature=signature,
        ):
            raise HTTPException(status_code=403, detail="طلب Voice غير موثق.")
        try:
            to_number = normalize_e164(params.get("To", ""))
        except CommunicationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        authorization = params.get("AlialiAuthorization", "")
        if not communication_auth_store.consume(authorization, to_number):
            raise HTTPException(status_code=403, detail="تفويض الاتصال غير صالح أو منتهي أو مستخدم.")
        caller_id = resolved_settings.twilio_voice_from_number
        if not caller_id:
            raise HTTPException(status_code=503, detail="رقم الاتصال غير مهيأ في الخادم.")
        from xml.sax.saxutils import escape as xml_escape
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Dial callerId="{xml_escape(caller_id)}"><Number>{xml_escape(to_number)}</Number></Dial>'
            '</Response>'
        )
        return Response(content=twiml, media_type="application/xml")

    @app.post("/api/v1/contact/sms")
    async def contact_sms(
        request: CommunicationRequest,
        x_telegram_init_data: str | None = Header(default=None),
        x_aliali_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        identity = authenticate_request(init_data, x_aliali_session)
        user = identity.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id is None:
            raise HTTPException(status_code=401, detail="تعذر تحديد هوية مستخدم Telegram.")
        enforce_communication_rate_limit(user_id)
        snapshot = evidence_snapshots.get(request.analysis_id)
        if not snapshot or snapshot.get("owner_id") != user_id or not snapshot.get("target_e164"):
            raise HTTPException(status_code=404, detail="نتيجة البحث غير متاحة لهذه الجلسة.")
        number = str(snapshot["target_e164"])
        try:
            import asyncio
            sid = await asyncio.to_thread(
                send_sms,
                account_sid=resolved_settings.twilio_account_sid,
                auth_token=resolved_settings.twilio_auth_token,
                from_number=resolved_settings.twilio_sms_from_number,
                to_number=number,
                body="هذه رسالة من Aliali. يمكنك تجاهلها إذا لم تكن تتوقعها.",
            )
        except CommunicationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"ok": True, "status": "sent", "provider": "twilio", "message_id": sid}

    @app.post("/api/v1/location/request")
    async def request_location(
        request: LocationRequest,
        x_telegram_init_data: str | None = Header(default=None),
        x_aliali_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        identity = authenticate_request(init_data, x_aliali_session)
        user = identity.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id is None:
            raise HTTPException(status_code=401, detail="تعذر تحديد هوية مستخدم Telegram.")
        enforce_communication_rate_limit(user_id)
        snapshot = evidence_snapshots.get(request.analysis_id)
        if not snapshot or snapshot.get("owner_id") != user_id or not snapshot.get("target_e164"):
            raise HTTPException(status_code=404, detail="نتيجة البحث غير متاحة لهذه الجلسة.")
        number = str(snapshot["target_e164"])
        try:
            request_id, token, expires_at = location_store.create(user_id)
            base = (resolved_settings.public_base_url or "").rstrip("/")
            if not base:
                raise CommunicationError("رابط Aliali العام غير مهيأ في الخادم.")
            share_url = f"{base}/share/location/{urllib.parse.quote(token, safe='')}"
            body = (
                "مرحبًا، هذا طلب لمشاركة موقعك من Aliali. "
                "إذا كنت موافقًا، افتح الرابط واختر مشاركة موقعي: "
                f"{share_url}"
            )
            import asyncio
            await asyncio.to_thread(
                send_sms,
                account_sid=resolved_settings.twilio_account_sid,
                auth_token=resolved_settings.twilio_auth_token,
                from_number=resolved_settings.twilio_voice_from_number,
                to_number=number,
                body=body,
            )
        except CommunicationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"ok": True, "request_id": request_id, "status": "pending", "expires_at": expires_at}

    @app.get("/api/v1/location/status/{request_id}")
    async def location_status(
        request_id: str,
        x_telegram_init_data: str | None = Header(default=None),
        x_aliali_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or ""
        identity = authenticate_request(init_data, x_aliali_session)
        user = identity.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id is None:
            raise HTTPException(status_code=401, detail="تعذر تحديد هوية مستخدم Telegram.")
        result = location_store.get(request_id, user_id)
        if not result:
            raise HTTPException(status_code=404, detail="طلب الموقع غير موجود.")
        return result

    @app.get("/share/location/{token}", response_class=HTMLResponse)
    async def location_share_page(token: str) -> str:
        return build_location_page(token)

    @app.post("/api/v1/location/{token}")
    async def submit_location(token: str, payload: LocationPayload) -> dict[str, object]:
        validate_coordinates(payload.latitude, payload.longitude, payload.accuracy_m)
        if not location_store.submit(token, payload.latitude, payload.longitude, payload.accuracy_m):
            raise HTTPException(status_code=410, detail="رابط مشاركة الموقع منتهي أو مستخدم.")
        return {"ok": True, "status": "received"}

    @app.post("/api/v1/lookup")
    async def lookup(
        request: LookupRequest,
        x_telegram_init_data: str | None = Header(default=None),
        x_aliali_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        identity = authenticate_request(init_data, x_aliali_session)
        user = identity.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id is None:
            raise HTTPException(status_code=401, detail="تعذر تحديد هوية مستخدم Telegram.")
        enforce_rate_limit(user_id)
        purge_expired_snapshots()
        try:
            result = await lookup_phone(request.target, resolved_settings)
            enforce_snapshot_quota(user_id)
            snapshot = create_evidence_snapshot(result)
            snapshot["owner_id"] = user_id
            evidence_snapshots[snapshot["analysis_id"]] = snapshot
            result["analysis_id"] = snapshot["analysis_id"]
            result["ai_analysis"] = {
                "status": "ready",
                "provider": None,
                "model": resolved_settings.openai_model if resolved_settings.ai_enabled else None,
                "message": "لقطة الأدلة جاهزة للتحليل دون إعادة تنفيذ البحث.",
            }
            snapshot["target_e164"] = result.get("e164")
            while len(evidence_snapshots) > max_snapshots:
                oldest = next(iter(evidence_snapshots))
                evidence_snapshots.pop(oldest, None)
            return result
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app
