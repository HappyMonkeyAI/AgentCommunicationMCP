"""Secret-safe readiness projection for canonical CLI profiles."""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from typing import Callable

from .cli_profiles import load_all_profiles, load_profile

_PROFILE_BINARIES = {
    "agy": "agy",
    "codex": "codex",
    "grok": "hermes",
    "hermes": "hermes",
    "kiro": "kiro",
    "opencode": "opencode",
}
def _default_auth_probe(provider_id: str) -> bool | None:
    """Return verified auth when a CLI offers a safe status command, else unknown."""
    if provider_id != "codex":
        return None
    try:
        result = subprocess.run(
            ["codex", "login", "status"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


class ProviderReadinessService:
    def __init__(
        self,
        *,
        executable_lookup: Callable[[str], str | None] = shutil.which,
        auth_probe: Callable[[str], object] = _default_auth_probe,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._executable_lookup = executable_lookup
        self._auth_probe = auth_probe
        self._clock = clock

    def get(self, profile_id: str) -> dict:
        return self._project(load_profile(profile_id))

    def list(self) -> list[dict]:
        return [self._project(profile) for profile in load_all_profiles()]

    def _project(self, profile: dict) -> dict:
        provider_id = str(profile["id"])
        binary = _PROFILE_BINARIES.get(provider_id)
        executable_available = bool(binary and self._executable_lookup(binary))
        auth_result = self._auth_probe(provider_id) if executable_available else False
        if not executable_available:
            state = "unavailable"
        elif auth_result is False:
            state = "authentication-needed"
        elif auth_result is None:
            state = "degraded"
        elif not profile.get("display_name") or not profile.get("kind"):
            state = "degraded"
        else:
            state = "ready"
        capabilities = list(dict.fromkeys([profile.get("kind"), *profile.get("tags", [])]))
        capabilities = [str(value) for value in capabilities if value]
        return {
            "id": provider_id,
            "display_name": profile.get("display_name") or provider_id,
            "binary": binary,
            "executable_available": executable_available,
            "state": state,
            "capabilities": capabilities,
            "diagnostics": {
                "executable": "available" if executable_available else "not-found",
                "authentication": (
                    "detected" if auth_result is True
                    else "not-detected" if auth_result is False
                    else "unknown"
                ),
            },
            "checked_at": self._clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
