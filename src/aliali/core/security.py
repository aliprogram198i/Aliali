from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AuthorizationLevel(StrEnum):
    PUBLIC = "public"
    AUTHORIZED = "authorized"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class AuthorizationContext:
    actor_id: int
    scope: str
    level: AuthorizationLevel
    case_id: str | None = None

    def allows(self, required: AuthorizationLevel) -> bool:
        order = {
            AuthorizationLevel.PUBLIC: 0,
            AuthorizationLevel.AUTHORIZED: 1,
            AuthorizationLevel.RESTRICTED: 2,
        }
        return order[self.level] >= order[required]
