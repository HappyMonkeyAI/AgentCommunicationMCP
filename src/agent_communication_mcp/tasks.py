from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .storage import SQLiteStore
from .cli_profiles import load_profile


def validate_preferred_cli_profile(profile_id: str | None) -> str | None:
    if profile_id is None or profile_id == "":
        return None
    load_profile(profile_id)
    return profile_id

TASK_STATES = {"submitted", "working", "input_required", "completed", "failed", "cancelled"}


class TaskService:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def drop_agent_message(self, agent_id: str, subject: str, body: str, artifacts: list[str] | None = None) -> dict[str, Any]:
        record = {
            "message_id": uuid.uuid4().hex,
            "agent_id": agent_id,
            "subject": subject,
            "body": body,
            "artifacts": artifacts or [],
            "created_at": _now(),
        }
        self.store.insert_message(record)
        return record

    def list_agent_inbox(self, agent_id: str) -> dict[str, Any]:
        return {"agent_id": agent_id, "messages": self.store.list_messages(agent_id), "tasks": self.store.list_tasks(agent_id)}

    def submit_task(
        self,
        agent_id: str,
        title: str,
        instructions: str,
        project_slug: str | None = None,
        artifacts: list[str] | None = None,
        preferred_cli_profile: str | None = None,
    ) -> dict[str, Any]:
        validated = validate_preferred_cli_profile(preferred_cli_profile)
        ts = _now()
        record = {
            "task_id": uuid.uuid4().hex,
            "agent_id": agent_id,
            "title": title,
            "instructions": instructions,
            "project_slug": project_slug,
            "artifacts": artifacts or [],
            "preferred_cli_profile": validated,
            "state": "submitted",
            "created_at": ts,
            "updated_at": ts,
        }
        self.store.insert_task(record)
        self.store.insert_event({"event_id": uuid.uuid4().hex, "task_id": record["task_id"], "state": "submitted", "message": "task submitted", "created_at": ts})
        return record

    def get_task(self, task_id: str) -> dict[str, Any]:
        task = self.store.get_task(task_id)
        if not task:
            raise KeyError(f"task not found: {task_id}")
        task["events"] = self.store.list_events(task_id)
        return task

    def append_task_event(self, task_id: str, state: str, message: str) -> dict[str, Any]:
        if state not in TASK_STATES:
            raise ValueError(f"invalid task state: {state}")
        if not self.store.get_task(task_id):
            raise KeyError(f"task not found: {task_id}")
        ts = _now()
        event = {"event_id": uuid.uuid4().hex, "task_id": task_id, "state": state, "message": message, "created_at": ts}
        self.store.insert_event(event)
        self.store.update_task_state(task_id, state, ts)
        return event


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
