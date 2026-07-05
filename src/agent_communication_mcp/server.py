from __future__ import annotations

from pathlib import Path
import os

from fastmcp import FastMCP

from .agent_cards import AgentDirectory
from .artifacts import ArtifactStore
from .auth import fastmcp_auth_provider, check_mcp_auth_and_scope
from .launcher_registry import LauncherRegistry
from .scopes import AuthorizationError
from .storage import SQLiteStore
from .tasks import TaskService

SERVICE_NAME = "agent-communication-mcp"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("AGENT_COMM_DATA_DIR", REPO_ROOT / ".agent-data"))

mcp = FastMCP("Agent Communication MCP", auth=fastmcp_auth_provider())
_directory = AgentDirectory.default()
_registry = LauncherRegistry(os.getenv("LAUNCHER_REGISTRY_PATH", Path.home() / "projects" / "launcher-project-registry" / "registry.json"))
_store = SQLiteStore(DATA_DIR / "tasks.sqlite3")
_tasks = TaskService(_store)
_artifacts = ArtifactStore(DATA_DIR / "artifacts")


def health() -> dict:
    """Return service status and storage location."""
    return {"status": "ok", "service": SERVICE_NAME, "data_dir": str(DATA_DIR)}


def list_agents() -> dict:
    """List known local agent identities and capabilities."""
    check_mcp_auth_and_scope("registry:read")
    agents = _directory.list_agents()
    return {"agents": agents, "count": len(agents)}


def get_agent_card(agent_id: str) -> dict:
    """Return an A2A-shaped agent card for a local agent."""
    check_mcp_auth_and_scope("registry:read")
    return {"agent": _directory.get_agent_card(agent_id), "found": True}


def list_projects(filter_query: str = "") -> dict:
    """List launcher-registry projects, optionally filtered by query."""
    check_mcp_auth_and_scope("registry:read")
    projects = _registry.list_projects(filter_query)
    return {"projects": projects, "count": len(projects)}


def get_project_context(slug: str) -> dict:
    """Read project CONTEXT.md and ADR list through launcher registry metadata."""
    check_mcp_auth_and_scope(f"fs:read:project:{slug}")
    return _registry.get_project_context(slug)


def resolve_project_workspace(slug: str) -> dict:
    """Resolve a launcher project slug to a workspace path."""
    check_mcp_auth_and_scope(f"fs:read:project:{slug}")
    return _registry.resolve_project_workspace(slug)


def drop_agent_message(agent_id: str, subject: str, body: str, artifacts: list[str] | None = None) -> dict:
    """Drop a durable message into an agent inbox."""
    check_mcp_auth_and_scope("mailbox:write")
    return _tasks.drop_agent_message(agent_id, subject, body, artifacts)


def list_agent_inbox(agent_id: str) -> dict:
    """List durable messages and tasks for an agent."""
    identity = check_mcp_auth_and_scope("mailbox:read")
    if identity.agent_id != agent_id and "*" not in identity.scopes:
        raise AuthorizationError(f"{identity.agent_id} is not authorized to read inbox for {agent_id}")
    return _tasks.list_agent_inbox(agent_id)


def submit_task(
    agent_id: str,
    title: str,
    instructions: str,
    project_slug: str | None = None,
    artifacts: list[str] | None = None,
    preferred_cli_profile: str | None = None,
) -> dict:
    """Submit an A2A-shaped task to a local agent. Optional preferred_cli_profile (codex, agy, …) is validated against YAML profiles."""
    check_mcp_auth_and_scope("task:submit")
    return _tasks.submit_task(
        agent_id,
        title,
        instructions,
        project_slug,
        artifacts,
        preferred_cli_profile=preferred_cli_profile,
    )


def get_task(task_id: str) -> dict:
    """Return a task with event history."""
    identity = check_mcp_auth_and_scope("mailbox:read")
    task = _tasks.get_task(task_id)
    if identity.agent_id != task["agent_id"] and "*" not in identity.scopes:
        raise AuthorizationError(f"{identity.agent_id} is not authorized to access task {task_id}")
    return task


def append_task_event(task_id: str, state: str, message: str) -> dict:
    """Append a state transition/event to a task."""
    identity = check_mcp_auth_and_scope("task:update")
    task = _tasks.get_task(task_id)
    if identity.agent_id != task["agent_id"] and "*" not in identity.scopes:
        raise AuthorizationError(f"{identity.agent_id} is not authorized to update task {task_id}")
    return _tasks.append_task_event(task_id, state, message)


def publish_artifact(task_id: str, name: str, content: str) -> dict:
    """Publish a text artifact under the service artifact root."""
    identity = check_mcp_auth_and_scope("artifact:write")
    task = _tasks.get_task(task_id)
    if identity.agent_id != task["agent_id"] and "*" not in identity.scopes:
        raise AuthorizationError(f"{identity.agent_id} is not authorized to publish artifacts for task {task_id}")
    return _artifacts.publish_content(task_id, name, content)


def list_artifacts(task_id: str) -> dict:
    """List artifacts for a task."""
    identity = check_mcp_auth_and_scope("artifact:read")
    task = _tasks.get_task(task_id)
    if identity.agent_id != task["agent_id"] and "*" not in identity.scopes:
        raise AuthorizationError(f"{identity.agent_id} is not authorized to list artifacts for task {task_id}")
    return {"task_id": task_id, "artifacts": _artifacts.list_artifacts(task_id)}


def read_artifact(artifact_id: str) -> dict:
    """Read a text artifact by id."""
    identity = check_mcp_auth_and_scope("artifact:read")
    artifact = _artifacts.read_artifact(artifact_id)
    task = _tasks.get_task(artifact["task_id"])
    if identity.agent_id != task["agent_id"] and "*" not in identity.scopes:
        raise AuthorizationError(f"{identity.agent_id} is not authorized to read artifact {artifact_id}")
    return artifact


def list_cli_profiles() -> dict:
    """List CLI agent profile ids (codex, agy, opencode, grok, kiro, hermes)."""
    check_mcp_auth_and_scope("registry:read")
    return {"profiles_dir": str(__import__("agent_communication_mcp.cli_profiles", fromlist=["profiles_dir"]).profiles_dir()), "profiles": list_cli_profiles_impl()}


def list_cli_profiles_impl() -> list[str]:
    from .cli_profiles import list_profile_ids
    return list_profile_ids()


def get_cli_profile(profile_id: str) -> dict:
    """Return one YAML CLI profile by id."""
    check_mcp_auth_and_scope("registry:read")
    from .cli_profiles import load_profile
    return {"profile": load_profile(profile_id), "found": True}


def suggest_cli_for_task(description: str, exclude_kinds: list[str] | None = None) -> dict:
    """Suggest best CLI agent profile for a task description (v0 keyword scoring)."""
    check_mcp_auth_and_scope("registry:read")
    return suggest_cli_for_task_impl(description, exclude_kinds=exclude_kinds)


def suggest_cli_for_task_impl(description: str, exclude_kinds: list[str] | None = None) -> dict:
    from .cli_profiles import suggest_cli_for_task as _suggest
    return _suggest(description, exclude_kinds=exclude_kinds)


def get_coordination_bootstrap() -> dict:
    """Paths and MCP tool names for CLI swarm routing (launcher registry + profiles)."""
    check_mcp_auth_and_scope("registry:read")
    from .cli_profiles import list_profile_ids, profiles_dir

    meta = _registry.get_agent_coordination_meta()
    teamwork = Path(meta["teamwork_repo"]).expanduser()
    return {
        "registry": meta,
        "profiles_dir": str(profiles_dir()),
        "profile_ids": list_profile_ids(),
        "agents_template_path": str(teamwork / meta["agents_template"]),
        "worker_routing_doc_path": str(teamwork / meta["worker_routing_doc"]),
        "mcp_routing_tools": [
            "get_coordination_bootstrap",
            "suggest_cli_for_task",
            "list_cli_profiles",
            "get_cli_profile",
            "submit_task",
        ],
        "submit_task_note": "Pass preferred_cli_profile to pin codex/agy/opencode; omit to let worker call suggest_cli_for_task on instructions.",
    }


for _tool in [
    health,
    list_agents,
    get_agent_card,
    list_projects,
    get_project_context,
    resolve_project_workspace,
    drop_agent_message,
    list_agent_inbox,
    submit_task,
    get_task,
    append_task_event,
    publish_artifact,
    list_artifacts,
    read_artifact,
    list_cli_profiles,
    get_cli_profile,
    suggest_cli_for_task,
    get_coordination_bootstrap,
]:
    mcp.tool()(_tool)


if __name__ == "__main__":
    mcp.run(transport="http", host=os.getenv("AGENT_COMM_HOST", "127.0.0.1"), port=int(os.getenv("AGENT_COMM_PORT", "8767")))
