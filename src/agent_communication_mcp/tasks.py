from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .cli_profiles import load_profile
from .storage import SQLiteStore

TASK_STATES = {"submitted", "working", "input_required", "completed", "failed", "cancelled"}

_ALLOWED_PLACEMENT_KEYS = {
    "decision",
    "host_id",
    "base_url",
    "platform",
    "reason",
    "sentinel_lease_id",
    "approval_required",
    "require_sentinel_lease",
    "approved",
}


def validate_preferred_cli_profile(profile_id: str | None) -> str | None:
    if profile_id is None or profile_id == "":
        return None
    load_profile(profile_id)
    return profile_id


def normalize_placement(
    *,
    placement: dict[str, Any] | None = None,
    placement_decision: str | None = None,
    placement_host_id: str | None = None,
    placement_base_url: str | None = None,
    sentinel_lease_id: str | None = None,
    approval_required: bool = False,
    require_sentinel_lease: bool = False,
) -> dict[str, Any] | None:
    merged: dict[str, Any] = {}
    if placement:
        if not isinstance(placement, dict):
            raise ValueError("placement must be an object")
        unknown = set(placement) - _ALLOWED_PLACEMENT_KEYS
        if unknown:
            raise ValueError(f"unsupported placement keys: {sorted(unknown)}")
        merged.update(placement)
    if placement_decision is not None:
        merged["decision"] = placement_decision
    if placement_host_id is not None:
        merged["host_id"] = placement_host_id
    if placement_base_url is not None:
        merged["base_url"] = placement_base_url
    if sentinel_lease_id is not None:
        merged["sentinel_lease_id"] = sentinel_lease_id
    if approval_required:
        merged["approval_required"] = True
    if require_sentinel_lease:
        merged["require_sentinel_lease"] = True
    if not merged:
        return None
    decision = merged.get("decision")
    if decision is not None and decision not in {"local", "peer", "none"}:
        raise ValueError("placement.decision must be local|peer|none")
    return merged


class TaskService:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def drop_agent_message(
        self, agent_id: str, subject: str, body: str, artifacts: list[str] | None = None
    ) -> dict[str, Any]:
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
        return {
            "agent_id": agent_id,
            "messages": self.store.list_messages(agent_id),
            "tasks": self.store.list_tasks(agent_id),
        }

    def submit_task(
        self,
        agent_id: str,
        title: str,
        instructions: str,
        project_slug: str | None = None,
        artifacts: list[str] | None = None,
        preferred_cli_profile: str | None = None,
        max_attempts: int = 3,
        *,
        placement: dict[str, Any] | None = None,
        placement_decision: str | None = None,
        placement_host_id: str | None = None,
        placement_base_url: str | None = None,
        sentinel_lease_id: str | None = None,
        approval_required: bool = False,
        require_sentinel_lease: bool = False,
    ) -> dict[str, Any]:
        validated = validate_preferred_cli_profile(preferred_cli_profile)
        normalized = normalize_placement(
            placement=placement,
            placement_decision=placement_decision,
            placement_host_id=placement_host_id,
            placement_base_url=placement_base_url,
            sentinel_lease_id=sentinel_lease_id,
            approval_required=approval_required,
            require_sentinel_lease=require_sentinel_lease,
        )
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
            "max_attempts": max(1, max_attempts),
            "placement": normalized,
        }
        self.store.insert_task(record)
        message = "task submitted"
        if normalized and normalized.get("approval_required"):
            message = "task submitted; awaiting approval before gated Hermes"
        self.store.insert_event(
            {
                "event_id": uuid.uuid4().hex,
                "task_id": record["task_id"],
                "state": "submitted",
                "message": message,
                "created_at": ts,
            }
        )
        return record

    def approve_task(self, task_id: str) -> dict[str, Any]:
        task = self.get_task(task_id)
        placement = dict(task.get("placement") or {})
        placement["approved"] = True
        placement["approval_required"] = bool(placement.get("approval_required", True))
        self.store.update_task_placement(task_id, placement, state="submitted")
        ts = _now()
        self.store.insert_event(
            {
                "event_id": uuid.uuid4().hex,
                "task_id": task_id,
                "state": "submitted",
                "message": "task approved for gated remote worker",
                "created_at": ts,
            }
        )
        return self.get_task(task_id)

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
        event = {
            "event_id": uuid.uuid4().hex,
            "task_id": task_id,
            "state": state,
            "message": message,
            "created_at": ts,
        }
        self.store.insert_event(event)
        self.store.update_task_state(task_id, state, ts)
        return event


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
