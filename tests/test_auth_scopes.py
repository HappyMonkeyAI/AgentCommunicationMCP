import pytest

from agent_communication_mcp.auth import AuthConfig, AuthenticationError, authenticate_token
from agent_communication_mcp.scopes import AuthorizationError, require_scope


def test_authenticate_token_returns_identity_from_config():
    config = AuthConfig.from_mapping({
        "dev-token": {"agent_id": "dev-agent", "scopes": ["registry:read"]}
    })

    identity = authenticate_token("dev-token", config)

    assert identity.agent_id == "dev-agent"
    assert identity.scopes == {"registry:read"}


def test_authenticate_token_rejects_unknown_token():
    config = AuthConfig.from_mapping({})

    with pytest.raises(AuthenticationError):
        authenticate_token("missing", config)


def test_require_scope_accepts_exact_scope_and_wildcard_prefix():
    identity = authenticate_token(
        "dev-token",
        AuthConfig.from_mapping({
            "dev-token": {"agent_id": "dev-agent", "scopes": ["registry:read", "fs:read:*"]}
        }),
    )

    require_scope(identity, "registry:read")
    require_scope(identity, "fs:read:project:launcher")


def test_require_scope_rejects_missing_scope():
    identity = authenticate_token(
        "dev-token",
        AuthConfig.from_mapping({"dev-token": {"agent_id": "dev-agent", "scopes": ["registry:read"]}}),
    )

    with pytest.raises(AuthorizationError):
        require_scope(identity, "mailbox:read")
