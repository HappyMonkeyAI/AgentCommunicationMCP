from agent_communication_mcp.agent_cards import AgentDirectory
from agent_communication_mcp.storage import SQLiteStore
from agent_communication_mcp.tasks import TaskService


def test_agent_directory_lists_default_agents():
    directory = AgentDirectory.default()

    ids = {agent["id"] for agent in directory.list_agents()}

    assert {"server-agent", "dev-agent", "desktop-agent"}.issubset(ids)
    assert directory.get_agent_card("dev-agent")["auth"]["scheme"] == "bearer"


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
