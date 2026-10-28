import pytest

from agent_communication_mcp.agent_cards import AgentDirectory
from agent_communication_mcp.storage import SQLiteStore
from agent_communication_mcp.tasks import TaskService


def test_agent_directory_lists_default_agents():
    directory = AgentDirectory.default()

    ids = {agent["id"] for agent in directory.list_agents()}

    assert {"server-agent", "dev-agent", "desktop-agent", "host-dev-215"}.issubset(ids)
    assert directory.get_agent_card("dev-agent")["auth"]["scheme"] == "bearer"
    host = directory.get_agent_card("host-dev-215")
    assert host["host_id"] == "dev-215"
    assert host["endpoints"]["resource_sentinel"] == "http://192.168.5.215:8800"
    assert "remote_hermes" in host["gates"]
    assert host["tool_belt"]["mode"] == "dynamic_proxy_summary"


def test_task_service_lifecycle_and_inbox(tmp_path):
    service = TaskService(SQLiteStore(tmp_path / "tasks.sqlite3"))

    message = service.drop_agent_message("dev-agent", "hello", "body", artifacts=[])
    task = service.submit_task("dev-agent", "Build", "Do work", project_slug="agent-communication-mcp", artifacts=[])
    service.append_task_event(task["task_id"], "working", "started")
    service.append_task_event(task["task_id"], "completed", "done")

    inbox = service.list_agent_inbox("dev-agent")
    saved = service.get_task(task["task_id"])

    assert message["agent_id"] == "dev-agent"
    assert saved["state"] == "completed"
    assert [event["state"] for event in saved["events"]] == ["submitted", "working", "completed"]
    assert len(inbox["messages"]) == 1
    assert len(inbox["tasks"]) == 1


def test_submit_task_stores_placement_and_approve_clears_gate(tmp_path):
    service = TaskService(SQLiteStore(tmp_path / "tasks.sqlite3"))
    task = service.submit_task(
        "dev-agent",
        "Remote",
        "Do remote work",
        project_slug="demo",
        placement_decision="peer",
        placement_host_id="dev-215",
        placement_base_url="http://192.168.5.215:8800",
        sentinel_lease_id="lease-1",
        approval_required=True,
        require_sentinel_lease=True,
    )
    assert task["placement"]["decision"] == "peer"
    assert task["placement"]["sentinel_lease_id"] == "lease-1"
    assert task["placement"]["approval_required"] is True

    approved = service.approve_task(task["task_id"])
    assert approved["placement"]["approved"] is True
    assert approved["state"] == "submitted"


def test_normalize_placement_rejects_unknown_keys(tmp_path):
    service = TaskService(SQLiteStore(tmp_path / "tasks.sqlite3"))
    with pytest.raises(ValueError, match="unsupported placement"):
        service.submit_task("dev-agent", "x", "y", placement={"evil": True})
