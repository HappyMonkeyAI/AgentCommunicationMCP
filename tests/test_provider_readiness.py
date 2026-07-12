from datetime import datetime, timezone

from agent_communication_mcp.provider_readiness import ProviderReadinessService


CHECKED_AT = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)


def test_provider_readiness_normalizes_canonical_profile():
    service = ProviderReadinessService(
        executable_lookup=lambda binary: f"/usr/bin/{binary}" if binary == "codex" else None,
        auth_probe=lambda provider_id: provider_id == "codex",
        clock=lambda: CHECKED_AT,
    )

    provider = service.get("codex")

    assert provider == {
        "id": "codex",
        "display_name": "OpenAI Codex CLI",
        "binary": "codex",
        "executable_available": True,
        "state": "ready",
        "capabilities": ["cli_coding", "openai", "greenfield", "refactor", "plan-execution"],
        "diagnostics": {"executable": "available", "authentication": "detected"},
        "checked_at": "2026-07-12T12:00:00Z",
    }


def test_provider_readiness_distinguishes_missing_binary_and_authentication():
    executable = {"codex": "/usr/bin/codex", "agy": None}
    service = ProviderReadinessService(
        executable_lookup=executable.get,
        auth_probe=lambda _provider_id: False,
        clock=lambda: CHECKED_AT,
    )

    assert service.get("agy")["state"] == "unavailable"
    codex = service.get("codex")
    assert codex["state"] == "authentication-needed"
    assert codex["diagnostics"] == {
        "executable": "available",
        "authentication": "not-detected",
    }


def test_provider_readiness_is_degraded_when_auth_cannot_be_verified():
    service = ProviderReadinessService(
        executable_lookup=lambda _binary: "/usr/bin/hermes",
        auth_probe=lambda _provider_id: None,
        clock=lambda: CHECKED_AT,
    )

    hermes = service.get("hermes")

    assert hermes["state"] == "degraded"
    assert hermes["diagnostics"]["authentication"] == "unknown"


def test_provider_diagnostics_never_expose_secret_probe_values():
    service = ProviderReadinessService(
        executable_lookup=lambda _binary: "/secret/path/codex",
        auth_probe=lambda _provider_id: "sk-secret-value",
        clock=lambda: CHECKED_AT,
    )

    serialized = repr(service.get("codex"))

    assert "sk-secret-value" not in serialized
    assert "/secret/path" not in serialized
