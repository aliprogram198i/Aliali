from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    NOT_AUTHORIZED = "not_authorized"
    MODULE_NOT_FOUND = "module_not_found"
    MODULE_DISABLED = "module_disabled"
    TIMEOUT = "timeout"
    DEPENDENCY_FAILURE = "dependency_failure"
    RATE_LIMITED = "rate_limited"
    INTERNAL = "internal"


@dataclass(frozen=True)
class SecurityError(Exception):
    code: ErrorCode
    message: str
    retryable: bool = False
    cause: str | None = None

    def __str__(self) -> str:
        return self.message
