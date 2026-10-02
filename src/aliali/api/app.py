from collections import defaultdict, deque
from time import monotonic

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..ai import analyze_with_openai, create_evidence_snapshot
from ..config import Settings
from ..core.errors import SecurityError
from .auth import create_session_token, validate_session_token, validate_telegram_init_data
from .phone import lookup_phone


class SessionRequest(BaseModel):
    init_data: str


class LookupRequest(SessionRequest):
    target: str


class AIAnalysisRequest(SessionRequest):
    analysis_id: str


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
    evidence_snapshots: dict[str, dict[str, object]] = {}
    rate_limit = 20
    window_seconds = 60.0

    def authenticate_request(init_data: str, session_token: str | None) -> dict[str, object]:
        if session_token:
            try:
                session = validate_session_token(session_token, resolved_settings.bot_token)
                return {"user": {"id": session["user_id"]}, "auth_date": None}
            except SecurityError:
                pass
        return _authenticate(init_data, resolved_settings)

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
        enforce_rate_limit(user_id)
        snapshot = evidence_snapshots.get(request.analysis_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="انتهت صلاحية لقطة الأدلة. أعد البحث ثم شغّل التحليل.")
        return await analyze_with_openai({}, resolved_settings, snapshot=snapshot)

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
        try:
            result = await lookup_phone(request.target)
            snapshot = create_evidence_snapshot(result)
            evidence_snapshots[snapshot["analysis_id"]] = snapshot
            result["analysis_id"] = snapshot["analysis_id"]
            result["ai_analysis"] = {
                "status": "ready",
                "provider": None,
                "model": resolved_settings.openai_model if resolved_settings.ai_enabled else None,
                "message": "لقطة الأدلة جاهزة للتحليل دون إعادة تنفيذ البحث.",
            }
            if len(evidence_snapshots) > 500:
                oldest = next(iter(evidence_snapshots))
                evidence_snapshots.pop(oldest, None)
            return result
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app
