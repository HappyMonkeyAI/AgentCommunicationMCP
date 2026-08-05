from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent_communication_mcp.storage import SQLiteStore
from agent_communication_mcp.tasks import TaskService
from agent_communication_mcp.worker import TaskWorker, WorkerResult


def test_claim_task_is_atomic_and_records_lease_and_attempt(tmp_path):
    store = SQLiteStore(tmp_path / "tasks.sqlite3")
    service = TaskService(store)
    task = service.submit_task("dev-agent", "Build", "Do work", max_attempts=2)

    claimed = store.claim_task("worker-a", lease_seconds=60)

    assert claimed["task_id"] == task["task_id"]
    assert claimed["state"] == "working"
    assert claimed["lease_owner"] == "worker-a"
    assert claimed["attempts"] == 1
    assert claimed["lease_expires_at"]
    assert store.claim_task("worker-b", lease_seconds=60) is None


def test_expired_working_task_can_be_reclaimed_and_capped(tmp_path):
    store = SQLiteStore(tmp_path / "tasks.sqlite3")
    service = TaskService(store)
    task = service.submit_task("dev-agent", "Build", "Do work", max_attempts=2)
    claimed = store.claim_task("worker-a", lease_seconds=1, now="2026-01-01T00:00:00Z")
    store.set_task_lease(task["task_id"], "worker-a", "2025-12-31T23:59:59Z", last_error="timeout")

    reclaimed = store.claim_task("worker-b", lease_seconds=60, now="2026-01-01T00:00:00Z")
    assert reclaimed["attempts"] == 2
    assert reclaimed["lease_owner"] == "worker-b"
    assert reclaimed["last_error"] == "timeout"

    store.set_task_lease(task["task_id"], "worker-b", "2025-12-31T23:59:59Z", last_error="again")
    assert store.claim_task("worker-c", lease_seconds=60, now="2026-01-01T00:00:00Z") is None
    assert store.get_task(task["task_id"])["state"] == "failed"


def test_worker_dry_run_builds_safe_hermes_command_without_launching(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = SQLiteStore(tmp_path / "tasks.sqlite3")
    task = TaskService(store).submit_task("dev-agent", "Build", "Do the thing", project_slug="demo")
    registry = {"projects": [{"slug": "demo", "path": str(workspace)}]}
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(__import__("json").dumps(registry))

    calls = []
    worker = TaskWorker(store, registry_path=registry_path, runner=lambda *args: calls.append(args))
    result = worker.run_once("worker-a", dry_run=True)

    assert result == WorkerResult(task_id=task["task_id"], state="dry-run")
    assert calls == []
    saved = store.get_task(task["task_id"])
    assert saved["state"] == "submitted"


def test_worker_executes_and_records_completed(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = SQLiteStore(tmp_path / "tasks.sqlite3")
    task = TaskService(store).submit_task("dev-agent", "Build", "Do the thing", project_slug="demo")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(__import__("json").dumps({"projects": [{"slug": "demo", "path": str(workspace)}]}))
    calls = []

    def runner(argv, cwd):
        calls.append((argv, cwd))
        return WorkerResult(returncode=0, stdout="ok", stderr="")

    result = TaskWorker(store, registry_path=registry_path, runner=runner).run_once("worker-a")

    assert result.state == "completed"
    assert calls[0][0] == ["/home/stephen/.local/bin/hermes", "chat", "--query", "Do the thing", "--quiet"]
    assert calls[0][1] == workspace
    assert [event["state"] for event in store.list_events(task["task_id"])] == ["submitted", "working", "completed"]


def test_worker_fails_without_valid_project_path(tmp_path):
    store = SQLiteStore(tmp_path / "tasks.sqlite3")
    task = TaskService(store).submit_task("dev-agent", "Build", "Do work", project_slug="missing")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text('{"projects": []}')

    result = TaskWorker(store, registry_path=registry_path, runner=lambda *args: None).run_once("worker-a")

    assert result.state == "failed"
    assert "project" in result.error.lower()
    assert store.get_task(task["task_id"])["last_error"]


def test_worker_module_help_is_available_without_launching_hermes():
    import subprocess, sys
    result = subprocess.run([sys.executable, "-m", "agent_communication_mcp.worker", "--help"], capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": "src"})
    assert result.returncode == 0
    assert "dry-run" in result.stdout


def test_main_passes_registry_path_from_environment_without_launching_hermes(tmp_path, monkeypatch, capsys):
    import agent_communication_mcp.worker as worker_module

    registry_path = tmp_path / "registry.json"
    captured = {}

    class FakeWorker:
        def __init__(self, store, registry_path=None):
            captured["registry_path"] = registry_path

        def run_once(self, owner, *, dry_run=False):
            captured["owner"] = owner
            captured["dry_run"] = dry_run
            return worker_module.WorkerResult(state="dry-run")

    monkeypatch.setenv("AGENT_COMM_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LAUNCHER_REGISTRY_PATH", str(registry_path))
    monkeypatch.setattr(worker_module, "TaskWorker", FakeWorker)

    assert worker_module.main(["--dry-run", "--owner", "test-worker"]) == 0

    assert captured == {
        "registry_path": str(registry_path),
        "owner": "test-worker",
        "dry_run": True,
    }
    assert capsys.readouterr().out == "dry-run\n"
