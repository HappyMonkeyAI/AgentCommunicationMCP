from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from fastmcp.server.dependencies import get_access_token


class AuthenticationError(ValueError):
    """Raised when a bearer token is missing or invalid."""


@dataclass(frozen=True)
class Identity:
    agent_id: str
    scopes: set[str]
    claims: dict[str, Any]


class AuthConfig:
    def __init__(self, tokens: dict[str, dict[str, Any]]):
        self.tokens = tokens

    @classmethod
    def from_mapping(cls, mapping: dict[str, dict[str, Any]]) -> "AuthConfig":
        normalized: dict[str, dict[str, Any]] = {}
        for token, data in mapping.items():
            scopes = data.get("scopes", [])
            normalized[token] = {
                **data,
                "agent_id": data.get("agent_id") or data.get("client_id") or "unknown-agent",
                "client_id": data.get("client_id") or data.get("agent_id") or "unknown-agent",
                "scopes": list(scopes),
            }
        return cls(normalized)

    @classmethod
    def from_env(cls) -> "AuthConfig":
        raw = os.getenv("AGENT_COMM_TOKENS_JSON")
        if raw:
            return cls.from_mapping(json.loads(raw))
        # Development-only defaults. Deployment docs require replacing these via env.
        return cls.from_mapping(default_token_mapping())

    def as_fastmcp_tokens(self) -> dict[str, dict[str, Any]]:
        return {
            token: {
                "client_id": data["client_id"],
                "scopes": data.get("scopes", []),
                "agent_id": data["agent_id"],
            }
            for token, data in self.tokens.items()
        }


def default_token_mapping() -> dict[str, dict[str, Any]]:
    return {
        "dev-token": {
            "agent_id": "dev-agent",
            "scopes": [
                "registry:read",
                "project_context:read",
                "artifact:read",
                "artifact:write",
                "mailbox:read",
                "mailbox:write",
                "task:submit",
                "task:update",
                "fs:read:project:*",
            ],
        },
        "server-token": {
            "agent_id": "server-agent",
            "scopes": [
                "registry:read",
                "project_context:read",
                "artifact:read",
                "artifact:write",
                "mailbox:read",
                "mailbox:write",
                "task:submit",
                "task:update",
                "fs:read:project:*",
                "fs:read:server:*",
            ],
        },
        "desktop-token": {
            "agent_id": "desktop-agent",
            "scopes": [
                "registry:read",
                "project_context:read",
                "artifact:read",
                "artifact:write",
                "mailbox:read",
                "mailbox:write",
                "task:submit",
                "task:update",
                "fs:read:desktop:*",
            ],
        },
    }


def authenticate_token(token: str | None, config: AuthConfig | None = None) -> Identity:
    if not token:
        raise AuthenticationError("missing bearer token")
    config = config or AuthConfig.from_env()
    data = config.tokens.get(token)
    if not data:
        raise AuthenticationError("invalid bearer token")
    return Identity(agent_id=data["agent_id"], scopes=set(data.get("scopes", [])), claims=data)


def fastmcp_auth_provider(config: AuthConfig | None = None):
    """Return FastMCP static bearer verifier for local/LAN deployment."""
    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

    config = config or AuthConfig.from_env()
    return StaticTokenVerifier(tokens=config.as_fastmcp_tokens())


def check_mcp_auth_and_scope(required_scope: str) -> Identity:
    """Enforce token validation and scope requirements in a FastMCP request context.

    If run under stdio transport (e.g. CLI or test), auth is bypassed to facilitate
    local run tools.
    """
    from fastmcp.server.context import _current_transport
    from .scopes import require_scope

    transport = _current_transport.get(None)
    if transport == "stdio":
        return Identity(agent_id="stdio-admin", scopes={"*"}, claims={})

    token = get_access_token()
    if not token:
        raise AuthenticationError("missing bearer token")

    identity = Identity(
        agent_id=token.client_id,
        scopes=set(token.scopes),
        claims=token.claims or {},
    )
    require_scope(identity, required_scope)
    return identity
