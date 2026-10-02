from collections import defaultdict, deque
from time import monotonic

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import Settings
from ..core.errors import SecurityError
from ..ai import analyze_with_openai
from .auth import validate_telegram_init_data
from .phone import lookup_phone


class SessionRequest(BaseModel):
    init_data: str


class LookupRequest(SessionRequest):
    target: str


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
            allow_headers=["Content-Type", "X-Telegram-Init-Data"],
        )

    # Process-local guardrail. It intentionally does not persist phone numbers or query targets.
    request_windows: dict[str, deque[float]] = defaultdict(deque)
    rate_limit = 20
    window_seconds = 60.0

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
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        identity = _authenticate(init_data, resolved_settings)
        return {
            "authenticated": True,
            "user": identity["user"],
            "auth_date": identity["auth_date"],
        }

    @app.post("/api/v1/ai-analysis")
    async def ai_analysis(
        request: LookupRequest,
        x_telegram_init_data: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        identity = _authenticate(init_data, resolved_settings)
        user = identity.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id is None:
            raise HTTPException(status_code=401, detail="تعذر تحديد هوية مستخدم Telegram.")
        enforce_rate_limit(user_id)
        try:
            result = await lookup_phone(request.target)
            return await analyze_with_openai(result, resolved_settings)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/lookup")
    async def lookup(
        request: LookupRequest,
        x_telegram_init_data: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        identity = _authenticate(init_data, resolved_settings)
        user = identity.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id is None:
            raise HTTPException(status_code=401, detail="تعذر تحديد هوية مستخدم Telegram.")
        enforce_rate_limit(user_id)
        try:
            return await lookup_phone(request.target)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app
