import pytest
from unittest.mock import patch
from fastmcp.server.context import _current_transport
from fastmcp.server.auth.auth import AccessToken
from agent_communication_mcp.scopes import AuthorizationError
from agent_communication_mcp.auth import AuthenticationError
from agent_communication_mcp.storage import SQLiteStore
from agent_communication_mcp.tasks import TaskService
from agent_communication_mcp.artifacts import ArtifactStore
from agent_communication_mcp.server import (
    list_agent_inbox,
    get_project_context,
    submit_task,
    get_task,
    append_task_event,
    publish_artifact,
    list_artifacts,
    read_artifact,
    _tasks,
    _artifacts,
    _registry,
)


@pytest.fixture
def http_transport():
    """Set transport context to HTTP to activate auth enforcement."""
    token = _current_transport.set("http")
    yield
    _current_transport.reset(token)


@pytest.fixture
def mock_registry(tmp_path):
    """Fixture to mock registry metadata."""
    import json
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(json.dumps({
        "projects": [
            {"slug": "alpha", "name": "Alpha Project", "path": str(tmp_path / "alpha")},
            {"slug": "beta", "name": "Beta Project", "path": str(tmp_path / "beta")},
        ]
    }), encoding="utf-8")
    
    (tmp_path / "alpha").mkdir()
    (tmp_path / "alpha" / "CONTEXT.md").write_text("# Alpha Context", encoding="utf-8")
    (tmp_path / "beta").mkdir()
    (tmp_path / "beta" / "CONTEXT.md").write_text("# Beta Context", encoding="utf-8")
    
    with patch("agent_communication_mcp.server._registry") as reg:
        from agent_communication_mcp.launcher_registry import LauncherRegistry
        reg.get_project_context.side_effect = LauncherRegistry(registry_file).get_project_context
        yield reg


@pytest.fixture
def mock_services(tmp_path):
    """Fixture to redirect storage/artifacts to temp directory."""
    db_path = tmp_path / "tasks.sqlite3"
    artifact_path = tmp_path / "artifacts"
    
    temp_store = SQLiteStore(db_path)
    temp_tasks = TaskService(temp_store)
    temp_artifacts = ArtifactStore(artifact_path)
    
    with patch("agent_communication_mcp.server._tasks", temp_tasks), \
         patch("agent_communication_mcp.server._artifacts", temp_artifacts):
        yield temp_tasks, temp_artifacts


def test_unauthenticated_calls_fail_closed(http_transport, mock_services):
    """Verify that calling tools without any bearer token raises AuthenticationError."""
    with patch("agent_communication_mcp.auth.get_access_token", return_value=None):
        with pytest.raises(AuthenticationError):
            list_agent_inbox("dev-agent")


def test_wrong_agent_inbox_access_is_blocked(http_transport, mock_services):
    """Verify that dev-agent cannot read server-agent's inbox."""
    dev_token = AccessToken(
        token="token-123",
        client_id="dev-agent",
        scopes=["mailbox:read"],
        claims={}
    )
    
    with patch("agent_communication_mcp.auth.get_access_token", return_value=dev_token):
        # dev-agent reading dev-agent inbox should succeed
        result = list_agent_inbox("dev-agent")
        assert result["agent_id"] == "dev-agent"
        
        # dev-agent reading server-agent inbox should be blocked
        with pytest.raises(AuthorizationError):
            list_agent_inbox("server-agent")


def test_cross_agent_task_and_artifact_access_is_blocked(http_transport, mock_services):
    """Verify that an agent cannot view, update, or read artifacts for another agent's tasks."""
    tasks_svc, artifacts_store = mock_services
    
    # 1. Submit a task assigned to server-agent
    task = tasks_svc.submit_task("server-agent", "Restart Service", "instructions")
    task_id = task["task_id"]
    
    # 2. Publish an artifact for this task (as server-agent)
    server_token = AccessToken(
        token="token-srv",
        client_id="server-agent",
        scopes=["artifact:write"],
        claims={}
    )
    with patch("agent_communication_mcp.auth.get_access_token", return_value=server_token):
        artifact = publish_artifact(task_id, "logs.txt", "system logs")
        artifact_id = artifact["artifact_id"]

    # 3. Verify dev-agent (even with correct scopes) is blocked from accessing server-agent's task/artifact
    dev_token = AccessToken(
        token="token-dev",
        client_id="dev-agent",
        scopes=["mailbox:read", "task:update", "artifact:read", "artifact:write"],
        claims={}
    )
    
    with patch("agent_communication_mcp.auth.get_access_token", return_value=dev_token):
        # dev-agent cannot get the task details
        with pytest.raises(AuthorizationError):
            get_task(task_id)
            
        # dev-agent cannot update the task state
        with pytest.raises(AuthorizationError):
            append_task_event(task_id, "working", "started")
            
        # dev-agent cannot publish artifacts for this task
        with pytest.raises(AuthorizationError):
            publish_artifact(task_id, "exploit.txt", "malicious payload")
            
        # dev-agent cannot list artifacts for this task
        with pytest.raises(AuthorizationError):
            list_artifacts(task_id)
            
        # dev-agent cannot read the specific artifact content
        with pytest.raises(AuthorizationError):
            read_artifact(artifact_id)


def test_dynamic_project_scope_enforcement(http_transport, mock_registry):
    """Verify that agent scopes are matched against dynamic project slugs."""
    # dev-agent has scoped project read access only for 'alpha'
    scoped_token = AccessToken(
        token="token-scoped",
        client_id="dev-agent",
        scopes=["fs:read:project:alpha"],
        claims={}
    )
    
    with patch("agent_communication_mcp.auth.get_access_token", return_value=scoped_token):
        # Reading project 'alpha' context should succeed
        alpha_ctx = get_project_context("alpha")
        assert alpha_ctx["found"] is True
        
        # Reading project 'beta' context should be blocked
        with pytest.raises(AuthorizationError):
            get_project_context("beta")

    # dev-agent has wildcard project read access
    wildcard_token = AccessToken(
        token="token-wildcard",
        client_id="dev-agent",
        scopes=["fs:read:project:*"],
        claims={}
    )
    
    with patch("agent_communication_mcp.auth.get_access_token", return_value=wildcard_token):
        # Reading project 'beta' context should now succeed
        beta_ctx = get_project_context("beta")
        assert beta_ctx["found"] is True


def test_artifact_path_component_safety(http_transport, mock_services):
    """Verify that path traversal attempts in artifact publishing are blocked."""
    tasks_svc, artifacts_store = mock_services
    
    # Submit task first to make it exist and pass task checks
    task = tasks_svc.submit_task("dev-agent", "Task Title", "instructions")
    task_id = task["task_id"]

    dev_token = AccessToken(
        token="token-dev",
        client_id="dev-agent",
        scopes=["artifact:write"],
        claims={}
    )
    
    with patch("agent_communication_mcp.auth.get_access_token", return_value=dev_token):
        # Path traversal characters (../) in artifact name should raise ValueError
        with pytest.raises(ValueError, match="unsafe path component"):
            publish_artifact(task_id, "../traversal.txt", "content")
