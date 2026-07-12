"""Bounded read-only activity and control-center projections."""

from __future__ import annotations

import json
from typing import Protocol

from .provider_readiness import ProviderReadinessService
from .storage import SQLiteStore


class _ProviderProjection(Protocol):
    def list(self) -> list[dict]: ...


class ActivityProjectionService:
    def __init__(
        self,
        store: SQLiteStore,
        *,
        providers: _ProviderProjection | None = None,
        default_limit: int | None = None,
        max_limit: int = 200,
    ) -> None:
        resolved_default = min(50, max_limit) if default_limit is None else default_limit
        if not 1 <= resolved_default <= max_limit:
            raise ValueError("default_limit must be within max_limit")
        self._store = store
        self._providers = providers or ProviderReadinessService()
        self.default_limit = resolved_default
        self.max_limit = max_limit

    def list(self, limit: int | None = None, *, agent_id: str | None = None) -> dict:
        effective_limit = self.default_limit if limit is None else limit
        if not 1 <= effective_limit <= self.max_limit:
            raise ValueError(f"limit must be between 1 and {self.max_limit}")
        activities = [self._project(row) for row in self._store.list_activity_events(effective_limit, agent_id)]
        return {
            "activities": activities,
            "count": len(activities),
            "limit": effective_limit,
            "max_limit": self.max_limit,
        }

    def control_center(self, limit: int | None = None) -> dict:
        providers = self._providers.list()
        activity = self.list(limit)
        activities = activity["activities"]
        return {
            "providers": providers,
            "activity": activity,
            "summary": {
                "provider_count": len(providers),
                "ready_provider_count": sum(provider.get("state") == "ready" for provider in providers),
                "activity_count": len(activities),
                "approval_required_count": sum(item["approval_required"] for item in activities),
            },
        }

    @staticmethod
    def _project(row: dict) -> dict:
        return {
            "id": row["event_id"],
            "task_ref": row["task_id"],
            "agent_ref": row["agent_id"],
            "project_ref": row["project_slug"],
            "state": row["state"],
            "summary": row["message"],
            "timestamp": row["created_at"],
            "approval_required": row["state"] == "input_required",
            "artifact_refs": json.loads(row["artifacts_json"]),
        }
