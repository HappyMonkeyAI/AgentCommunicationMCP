import pytest

from agent_communication_mcp.launcher_registry import LauncherRegistry
from agent_communication_mcp.storage import SQLiteStore
from agent_communication_mcp.tasks import TaskService, validate_preferred_cli_profile
from fastmcp.server.context import _current_transport

from agent_communication_mcp.server import get_coordination_bootstrap, submit_task


def test_validate_preferred_cli_profile():
    assert validate_preferred_cli_profile(None) is None
    assert validate_preferred_cli_profile("codex") == "codex"
    with pytest.raises(KeyError):
        validate_preferred_cli_profile("not-a-profile")


def test_submit_task_stores_preferred_cli_profile(tmp_path):
    service = TaskService(SQLiteStore(tmp_path / "t.sqlite3"))
    task = service.submit_task(
        "dev-agent",
        "Implement",
        "Add adapter",
        preferred_cli_profile="agy",
    )
    saved = service.get_task(task["task_id"])
    assert saved["preferred_cli_profile"] == "agy"


def test_launcher_agent_coordination_meta():
    reg = LauncherRegistry()
    meta = reg.get_agent_coordination_meta()
    assert "teamwork_repo" in meta
    assert "cli_profiles_dir" in meta


def test_get_coordination_bootstrap_stdio():
    _current_transport.set("stdio")
    boot = get_coordination_bootstrap()
    assert "codex" in boot["profile_ids"]
    assert boot["registry"]["teamwork_repo"]