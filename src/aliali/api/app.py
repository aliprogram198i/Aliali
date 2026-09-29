from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import Settings
from ..core.errors import SecurityError
from ..core.registry import ModuleRegistry
from ..modules.facebook import FACEBOOK_MODULES
from ..modules.network import NETWORK_MODULES
from .auth import validate_telegram_init_data
from .network import normalize_target, reverse_dns, tcp_connectivity


class SessionRequest(BaseModel):
    init_data: str


class NetworkOperationRequest(SessionRequest):
    module_key: str
    operation: str
    ip: str | None = None
    mac: str | None = None
    port: int | None = None


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    for module in [*FACEBOOK_MODULES, *NETWORK_MODULES]:
        registry.register(module)
    return registry


def _authenticate(
    init_data: str,
    settings: Settings,
) -> dict[str, object]:
    try:
        return validate_telegram_init_data(init_data, settings.bot_token)
    except SecurityError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc


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
        identity = _authenticate(init_data, resolved_settings)
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

    @app.post("/api/v1/dashboard")
    async def dashboard(
        request: SessionRequest,
        x_telegram_init_data: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        _authenticate(init_data, resolved_settings)

        registry = _registry()
        modules = [
            {
                "key": module.key,
                "title": module.title,
                "description": module.description,
                "category": module.category,
                "enabled": module.enabled,
            }
            for module in registry.all()
            if module.enabled
        ]
        categories = sorted({module["category"] for module in modules})
        return {
            "status": "operational",
            "data_source": "module_registry",
            "metrics": {
                "assets": None,
                "changes": None,
                "evidence": None,
            },
            "module_summary": {
                "total_enabled": len(modules),
                "categories": categories,
            },
            "modules": modules,
        }

    @app.post("/api/v1/network/operate")
    async def network_operate(
        request: NetworkOperationRequest,
        x_telegram_init_data: str | None = Header(default=None),
    ) -> dict[str, object]:
        init_data = x_telegram_init_data or request.init_data
        _authenticate(init_data, resolved_settings)

        registry = _registry()
        module = registry.get(request.module_key)
        if module is None or not module.enabled or module.category != "network":
            raise HTTPException(status_code=404, detail="Network module not found")

        try:
            target = normalize_target(ip=request.ip, mac=request.mac)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if target.kind not in module.metadata.get("identifier_types", []):
            raise HTTPException(
                status_code=422,
                detail=f"Module does not accept {target.kind.upper()} targets",
            )

        if request.operation == "validate":
            return {
                "ok": True,
                "operation": "validate",
                "module": module.key,
                "target": {"type": target.kind, "value": target.value},
                "message": "الهدف صالح ومطابق لنوع الوحدة.",
            }

        if request.operation == "reverse_dns":
            if target.kind != "ip":
                raise HTTPException(
                    status_code=422,
                    detail="Reverse DNS requires an IP address",
                )
            hostname = reverse_dns(target.value)
            return {
                "ok": True,
                "operation": "reverse_dns",
                "module": module.key,
                "target": {"type": target.kind, "value": target.value},
                "hostname": hostname,
                "message": (
                    "تم العثور على اسم مضيف."
                    if hostname
                    else "لم يتم العثور على اسم مضيف عبر Reverse DNS."
                ),
            }

        if request.operation == "connectivity":
            if target.kind != "ip" or request.port is None:
                raise HTTPException(
                    status_code=422,
                    detail="Connectivity test requires an IP address and port",
                )
            reachable = tcp_connectivity(target.value, request.port)
            return {
                "ok": True,
                "operation": "connectivity",
                "module": module.key,
                "target": {"type": target.kind, "value": target.value},
                "port": request.port,
                "reachable": reachable,
                "message": (
                    "الاتصال بالمنفذ نجح."
                    if reachable
                    else "تعذر إنشاء اتصال بالمنفذ ضمن مهلة الاختبار."
                ),
            }

        raise HTTPException(status_code=400, detail="Unsupported network operation")

    return app
