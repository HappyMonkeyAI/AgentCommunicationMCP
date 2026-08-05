from __future__ import annotations

import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .launcher_registry import LauncherRegistry
from .storage import SQLiteStore
from .tasks import _now

MAX_OUTPUT = 64 * 1024


@dataclass(frozen=True)
class WorkerResult:
    task_id: str | None = None
    state: str = "idle"
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str = ""


class TaskWorker:
    def __init__(self, store: SQLiteStore, registry_path: str | Path | None = None, runner: Callable | None = None, lease_seconds: int = 300, max_output: int = MAX_OUTPUT, hermes_bin: str | None = None):
        self.store = store
        self.registry = LauncherRegistry(registry_path) if registry_path is not None else LauncherRegistry()
        self.runner = runner or self._run_subprocess
        self.hermes_bin = hermes_bin or os.getenv("HERMES_BIN", "hermes")
        self.lease_seconds = lease_seconds
        self.max_output = max_output

    def run_once(self, owner: str, *, dry_run: bool = False) -> WorkerResult:
        task = self.store.claim_task(owner, lease_seconds=self.lease_seconds)
        if task is None:
            return WorkerResult(state="idle")
        self.store.insert_event({"event_id": uuid.uuid4().hex, "task_id": task["task_id"], "state": "working", "message": "worker claimed task", "created_at": _now()})
        if dry_run:
            self.store.set_task_lease(task["task_id"], owner, None)
            self.store.update_task_state(task["task_id"], "submitted", _now())
            return WorkerResult(task_id=task["task_id"], state="dry-run")
        try:
            workspace = self.registry.resolve_project_workspace(task["project_slug"] or "")
            if not workspace.get("found") or not workspace.get("is_dir"):
                raise ValueError(f"project workspace is not valid: {task.get('project_slug')!r}")
            argv = [self.hermes_bin, "chat", "--query", task["instructions"], "--quiet"]
            result = self.runner(argv, Path(workspace["path"]))
            if result.returncode == 0:
                self.store.finish_task(task["task_id"], owner, "completed", "hermes completed", last_error=None)
                return WorkerResult(task_id=task["task_id"], state="completed", returncode=result.returncode, stdout=_bounded(result.stdout, self.max_output), stderr=_bounded(result.stderr, self.max_output))
            error = _bounded(result.stderr or result.stdout or f"hermes exited {result.returncode}", self.max_output)
            self.store.finish_task(task["task_id"], owner, "failed", "hermes failed", last_error=error)
            return WorkerResult(task_id=task["task_id"], state="failed", returncode=result.returncode, stdout=_bounded(result.stdout, self.max_output), stderr=_bounded(result.stderr, self.max_output), error=error)
        except Exception as exc:
            error = _bounded(str(exc), self.max_output)
            self.store.finish_task(task["task_id"], owner, "failed", "worker failed", last_error=error)
            return WorkerResult(task_id=task["task_id"], state="failed", error=error)

    def _run_subprocess(self, argv: Sequence[str], cwd: Path) -> WorkerResult:
        completed = subprocess.run(list(argv), cwd=cwd, capture_output=True, text=True, timeout=3600, check=False)
        return WorkerResult(returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def _bounded(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit] + "…"


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Run one durable Agent Communication MCP task worker cycle")
    parser.add_argument("--once", action="store_true", help="run one cycle (the default)")
    parser.add_argument("--dry-run", action="store_true", help="claim and inspect one task without launching Hermes")
    parser.add_argument("--owner", default="agent-communication-worker")
    args = parser.parse_args(argv)
    import os
    data_dir = Path(os.getenv("AGENT_COMM_DATA_DIR", ".agent-data"))
    registry_path = os.getenv("LAUNCHER_REGISTRY_PATH")
    hermes_bin = os.getenv("HERMES_BIN")
    worker_kwargs = {"registry_path": registry_path}
    if hermes_bin:
        worker_kwargs["hermes_bin"] = hermes_bin
    result = TaskWorker(SQLiteStore(data_dir / "tasks.sqlite3"), **worker_kwargs).run_once(args.owner, dry_run=args.dry_run)
    print(result.state)
    return 0 if result.state in {"idle", "dry-run", "completed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
