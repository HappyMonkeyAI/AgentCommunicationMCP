import json
from pathlib import Path

from agent_communication_mcp.launcher_registry import LauncherRegistry


def test_launcher_registry_lists_and_filters_projects(tmp_path):
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"projects": [
        {"slug": "alpha", "name": "Alpha", "path": str(tmp_path / "alpha"), "tech_stack": ["python"], "summary": "First"},
        {"slug": "beta", "name": "Beta", "path": str(tmp_path / "beta"), "tech_stack": ["node"], "summary": "Second"},
    ]}), encoding="utf-8")

    result = LauncherRegistry(registry).list_projects("python")

    assert [p["slug"] for p in result] == ["alpha"]


def test_get_project_context_reads_context_and_adr_count(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "CONTEXT.md").write_text("# Context\nImportant", encoding="utf-8")
    (project / "docs" / "adr").mkdir(parents=True)
    (project / "docs" / "adr" / "0001-test.md").write_text("# ADR", encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"projects": [{"slug": "proj", "name": "Proj", "path": str(project)}]}), encoding="utf-8")

    context = LauncherRegistry(registry).get_project_context("proj")

    assert context["found"] is True
    assert "Important" in context["context_md"]
    assert context["adr_count"] == 1


def test_resolve_project_workspace_returns_resolved_path(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"projects": [{"slug": "proj", "name": "Proj", "path": str(project)}]}), encoding="utf-8")

    result = LauncherRegistry(registry).resolve_project_workspace("proj")

    assert result["path"] == str(project.resolve())
