from __future__ import annotations

import os
from pathlib import Path

from fastmcp import FastMCP

from .agent_cards import AgentDirectory
from .artifacts import ArtifactStore
from .auth import fastmcp_auth_provider
from .launcher_registry import LauncherRegistry
from .storage import SQLiteStore
from .tasks import TaskService

SERVICE_NAME = "agent-communication-mcp"
DATA_DIR = Path(os.getenv("AGENT_COMM_DATA_DIR", "/home/stephen/projects/agent-communication-mcp/.agent-data"))

mcp = FastMCP("Agent Communication MCP", auth=fastmcp_auth_provider())
_directory = AgentDirectory.default()
_registry = LauncherRegistry(os.getenv("LAUNCHER_REGISTRY_PATH", "/home/stephen/projects/launcher-project-registry/registry.json"))
_store = SQLiteStore(DATA_DIR / "tasks.sqlite3")
_tasks = TaskService(_store)
_artifacts = ArtifactStore(DATA_DIR / "artifacts")


def health() -> dict:
    """Return service status and storage location."""
    return {"status": "ok", "service": SERVICE_NAME, "data_dir": str(DATA_DIR)}


def list_agents() -> dict:
    """List known local agent identities and capabilities."""
    agents = _directory.list_agents()
    return {"agents": agents, "count": len(agents)}


def get_agent_card(agent_id: str) -> dict:
    """Return an A2A-shaped agent card for a local agent."""
    return {"agent": _directory.get_agent_card(agent_id), "found": True}


def list_projects(filter_query: str = "") -> dict:
    """List launcher-registry projects, optionally filtered by query."""
    projects = _registry.list_projects(filter_query)
    return {"projects": projects, "count": len(projects)}


def get_project_context(slug: str) -> dict:
    """Read project CONTEXT.md and ADR list through launcher registry metadata."""
    return _registry.get_project_context(slug)


def resolve_project_workspace(slug: str) -> dict:
    """Resolve a launcher project slug to a workspace path."""
    return _registry.resolve_project_workspace(slug)


def drop_agent_message(agent_id: str, subject: str, body: str, artifacts: list[str] | None = None) -> dict:
    """Drop a durable message into an agent inbox."""
    return _tasks.drop_agent_message(agent_id, subject, body, artifacts)


def list_agent_inbox(agent_id: str) -> dict:
    """List durable messages and tasks for an agent."""
    return _tasks.list_agent_inbox(agent_id)


def submit_task(agent_id: str, title: str, instructions: str, project_slug: str | None = None, artifacts: list[str] | None = None) -> dict:
    """Submit an A2A-shaped task to a local agent."""
    return _tasks.submit_task(agent_id, title, instructions, project_slug, artifacts)


def get_task(task_id: str) -> dict:
    """Return a task with event history."""
    return _tasks.get_task(task_id)


def append_task_event(task_id: str, state: str, message: str) -> dict:
    """Append a state transition/event to a task."""
    return _tasks.append_task_event(task_id, state, message)


def publish_artifact(task_id: str, name: str, content: str) -> dict:
    """Publish a text artifact under the service artifact root."""
    return _artifacts.publish_content(task_id, name, content)


def list_artifacts(task_id: str) -> dict:
    """List artifacts for a task."""
    return {"task_id": task_id, "artifacts": _artifacts.list_artifacts(task_id)}


def read_artifact(artifact_id: str) -> dict:
    """Read a text artifact by id."""
    return _artifacts.read_artifact(artifact_id)


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
]:
    mcp.tool()(_tool)


if __name__ == "__main__":
    mcp.run(transport="http", host=os.getenv("AGENT_COMM_HOST", "127.0.0.1"), port=int(os.getenv("AGENT_COMM_PORT", "8767")))
