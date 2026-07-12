import pytest

from agent_communication_mcp.activity import ActivityProjectionService
from agent_communication_mcp.storage import SQLiteStore


def _seed_task(store, task_id, agent_id, project_slug, timestamp, artifacts=None):
    store.insert_task(
        {
            "task_id": task_id,
            "agent_id": agent_id,
            "title": f"Task {task_id}",
            "instructions": "work",
            "project_slug": project_slug,
            "artifacts": artifacts or [],
            "state": "submitted",
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )


def test_activity_projection_is_newest_first_and_bounded(tmp_path):
    store = SQLiteStore(tmp_path / "tasks.sqlite3")
    _seed_task(store, "task-a", "dev-agent", "alpha", "2026-07-12T10:00:00Z", ["artifact-a"])
    _seed_task(store, "task-b", "server-agent", "beta", "2026-07-12T11:00:00Z")
    store.insert_event({"event_id": "event-a", "task_id": "task-a", "state": "working", "message": "started", "created_at": "2026-07-12T10:01:00Z"})
    store.insert_event({"event_id": "event-b", "task_id": "task-b", "state": "completed", "message": "finished", "created_at": "2026-07-12T11:01:00Z"})

    result = ActivityProjectionService(store, default_limit=10, max_limit=25).list(limit=1)

    assert result["limit"] == 1
    assert result["max_limit"] == 25
    assert result["activities"] == [
        {
            "id": "event-b",
            "task_ref": "task-b",
            "agent_ref": "server-agent",
            "project_ref": "beta",
            "state": "completed",
            "summary": "finished",
            "timestamp": "2026-07-12T11:01:00Z",
            "approval_required": False,
            "artifact_refs": [],
        }
    ]


def test_activity_projection_marks_input_required_as_approval_required(tmp_path):
    store = SQLiteStore(tmp_path / "tasks.sqlite3")
    _seed_task(store, "task-a", "dev-agent", "alpha", "2026-07-12T10:00:00Z")
    store.insert_event({"event_id": "event-a", "task_id": "task-a", "state": "input_required", "message": "approve deploy", "created_at": "2026-07-12T10:01:00Z"})

    activity = ActivityProjectionService(store).list()["activities"][0]

    assert activity["approval_required"] is True


def test_activity_projection_filters_to_authenticated_agent(tmp_path):
    store = SQLiteStore(tmp_path / "tasks.sqlite3")
    _seed_task(store, "task-dev", "dev-agent", "alpha", "2026-07-12T10:00:00Z")
    _seed_task(store, "task-server", "server-agent", "beta", "2026-07-12T11:00:00Z")
    store.insert_event({"event_id": "event-dev", "task_id": "task-dev", "state": "working", "message": "dev private", "created_at": "2026-07-12T10:01:00Z"})
    store.insert_event({"event_id": "event-server", "task_id": "task-server", "state": "working", "message": "server private", "created_at": "2026-07-12T11:01:00Z"})

    activities = ActivityProjectionService(store).list(agent_id="dev-agent")["activities"]

    assert [item["id"] for item in activities] == ["event-dev"]
    assert "server private" not in repr(activities)


@pytest.mark.parametrize("limit", [0, -1, 26])
def test_activity_projection_rejects_limits_outside_configured_bound(tmp_path, limit):
    service = ActivityProjectionService(SQLiteStore(tmp_path / "tasks.sqlite3"), max_limit=25)

    with pytest.raises(ValueError, match="limit must be between 1 and 25"):
        service.list(limit=limit)


def test_control_center_reuses_provider_and_activity_projections(tmp_path):
    class Providers:
        def list(self):
            return [{"id": "codex", "state": "ready"}, {"id": "agy", "state": "unavailable"}]

    service = ActivityProjectionService(SQLiteStore(tmp_path / "tasks.sqlite3"), providers=Providers())

    control_center = service.control_center(limit=5)

    assert control_center["providers"][0]["id"] == "codex"
    assert control_center["activity"]["activities"] == []
    assert control_center["summary"] == {"provider_count": 2, "ready_provider_count": 1, "activity_count": 0, "approval_required_count": 0}
