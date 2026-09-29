from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import Settings
from ..core.errors import SecurityError
from .auth import validate_telegram_init_data


class SessionRequest(BaseModel):
    init_data: str


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title="Aliali API", version="0.1.0")

    origins = [resolved_settings.mini_app_url] if resolved_settings.mini_app_url else []
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["POST", "GET"],
            allow_headers=["Content-Type", "X-Telegram-Init-Data"],
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/session")
    async def create_session(
        request: SessionRequest,
        x_telegram_init_data: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        try:
            identity = validate_telegram_init_data(init_data, resolved_settings.bot_token)
        except SecurityError as exc:
            raise HTTPException(status_code=401, detail=exc.message) from exc

        return {
            "authenticated": True,
            "user": identity["user"],
            "auth_date": identity["auth_date"],
            "capabilities": {
                "dashboard": True,
                "network": True,
                "cases": False,
                "reports": False,
            },
        }

    return app
