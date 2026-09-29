from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .errors import ErrorCode, SecurityError
from .security import AuthorizationContext, AuthorizationLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutionPolicy:
    timeout_seconds: float = 30.0
    required_authorization: AuthorizationLevel = AuthorizationLevel.PUBLIC


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    module_key: str
    data: dict[str, Any] | None = None
    error_code: ErrorCode | None = None
    error_message: str | None = None


async def execute(
    module_key: str,
    operation: Callable[[], Awaitable[dict[str, Any]]],
    context: AuthorizationContext,
    policy: ExecutionPolicy,
) -> ExecutionResult:
    if not context.allows(policy.required_authorization):
        return ExecutionResult(
            ok=False,
            module_key=module_key,
            error_code=ErrorCode.NOT_AUTHORIZED,
            error_message="The requested operation is outside the current authorization scope.",
        )

    try:
        data = await asyncio.wait_for(operation(), timeout=policy.timeout_seconds)
        return ExecutionResult(ok=True, module_key=module_key, data=data)
    except asyncio.TimeoutError:
        return ExecutionResult(
            ok=False,
            module_key=module_key,
            error_code=ErrorCode.TIMEOUT,
            error_message="The module exceeded its execution budget.",
        )
    except SecurityError as exc:
        logger.warning("module=%s code=%s", module_key, exc.code)
        return ExecutionResult(
            ok=False,
            module_key=module_key,
            error_code=exc.code,
            error_message=exc.message,
        )
    except Exception:
        logger.exception("Unhandled module failure: %s", module_key)
        return ExecutionResult(
            ok=False,
            module_key=module_key,
            error_code=ErrorCode.INTERNAL,
            error_message="The operation failed safely; no partial result was promoted.",
        )
