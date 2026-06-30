from __future__ import annotations

from pathlib import Path
from typing import Mapping


class PathSandboxError(ValueError):
    """Raised when a path escapes its approved sandbox root."""


class PathSandbox:
    def __init__(self, roots: Mapping[str, str | Path]):
        self.roots = {name: Path(path).expanduser().resolve() for name, path in roots.items()}

    def resolve(self, scope: str, relative_path: str | Path) -> Path:
        if scope not in self.roots:
            raise PathSandboxError(f"unknown filesystem scope: {scope}")
        raw = Path(relative_path)
        if raw.is_absolute():
            raise PathSandboxError("absolute paths are not accepted; use a named scope")
        root = self.roots[scope]
        candidate = (root / raw).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise PathSandboxError(f"path escapes scope {scope}") from exc
        return candidate
