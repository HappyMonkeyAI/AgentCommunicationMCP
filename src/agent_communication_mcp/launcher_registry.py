from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_REGISTRY_PATH = Path("/home/stephen/projects/launcher-project-registry/registry.json")


class LauncherRegistry:
    def __init__(self, registry_path: str | Path = DEFAULT_REGISTRY_PATH):
        self.registry_path = Path(registry_path)

    def _load(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {"projects": []}
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def list_projects(self, filter_query: str = "") -> list[dict[str, Any]]:
        projects = list(self._load().get("projects", []))
        if not filter_query:
            return projects
        q = filter_query.lower()
        return [
            p
            for p in projects
            if q in str(p.get("name", "")).lower()
            or q in str(p.get("slug", "")).lower()
            or q in str(p.get("summary", "")).lower()
            or any(q in str(t).lower() for t in p.get("tech_stack", []))
            or any(q in str(t).lower() for t in p.get("tags", []))
        ]

    def get_project(self, slug: str) -> dict[str, Any] | None:
        for project in self._load().get("projects", []):
            if project.get("slug") == slug:
                return project
        return None

    def resolve_project_workspace(self, slug: str) -> dict[str, Any]:
        project = self.get_project(slug)
        if not project:
            return {"found": False, "error": "project not found", "slug": slug}
        raw_path = project.get("path")
        if not raw_path:
            return {"found": False, "error": "project has no path", "slug": slug}
        path = Path(raw_path).expanduser().resolve()
        return {"found": path.exists(), "slug": slug, "path": str(path), "is_dir": path.is_dir()}

    def get_project_context(self, slug: str, max_chars: int = 12000) -> dict[str, Any]:
        workspace = self.resolve_project_workspace(slug)
        if not workspace.get("found"):
            return {**workspace, "context_md": "", "adr_count": 0, "adrs": []}
        root = Path(workspace["path"])
        context_path = root / "CONTEXT.md"
        context = ""
        if context_path.exists():
            context = context_path.read_text(encoding="utf-8", errors="replace")[:max_chars]
        adr_dir = root / "docs" / "adr"
        adrs = sorted(str(p.relative_to(root)) for p in adr_dir.glob("*.md")) if adr_dir.exists() else []
        return {
            "found": True,
            "slug": slug,
            "path": str(root),
            "context_path": str(context_path),
            "context_md": context,
            "adr_count": len(adrs),
            "adrs": adrs,
        }
