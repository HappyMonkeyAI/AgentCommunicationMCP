from __future__ import annotations

from dataclasses import dataclass

from .auth import Identity


class AuthorizationError(PermissionError):
    """Raised when an authenticated identity lacks a required scope."""


@dataclass(frozen=True)
class ScopeCheck:
    required: str
    granted: str | None


def _matches(granted: str, required: str) -> bool:
    if granted == required or granted == "*":
        return True
    if granted.endswith(":*"):
        return required.startswith(granted[:-1])
    return False


def has_scope(identity: Identity, required: str) -> ScopeCheck:
    for granted in sorted(identity.scopes):
        if _matches(granted, required):
            return ScopeCheck(required=required, granted=granted)
    return ScopeCheck(required=required, granted=None)


def require_scope(identity: Identity, required: str) -> None:
    check = has_scope(identity, required)
    if check.granted is None:
        raise AuthorizationError(f"{identity.agent_id} lacks required scope: {required}")
