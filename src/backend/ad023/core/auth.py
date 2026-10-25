"""Authorization contracts (C4). How a Principal is authenticated (token,
session) is out of scope: authentication is still [CÒN MỞ] for APP-05."""

from dataclasses import dataclass, field
from typing import Protocol


class AccessDenied(PermissionError):
    """Raised for both 'not allowed' and 'does not exist' so callers cannot
    enumerate buildings or devices they have no access to (maps to HTTP 403)."""


@dataclass(frozen=True)
class Principal:
    user_id: str
    building_scopes: frozenset = field(default_factory=frozenset)


class AuthPolicy(Protocol):
    def can_view_building(self, principal: Principal, building_id: str) -> bool: ...


class ScopeAuthPolicy:
    def can_view_building(self, principal, building_id):
        return principal is not None and building_id in principal.building_scopes


class AuditLog:
    """In-memory audit sink; records ids only, never payloads or values."""

    def __init__(self):
        self.events = []

    def denied(self, principal, action, target):
        self.events.append({
            "outcome": "denied",
            "action": action,
            "user_id": getattr(principal, "user_id", None),
            "target": target,
        })
