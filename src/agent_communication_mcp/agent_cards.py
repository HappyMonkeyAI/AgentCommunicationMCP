from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentCard:
    id: str
    name: str
    description: str
    endpoint: str
    capabilities: list[str]
    scopes: list[str]
    auth: dict[str, str]
    host_id: str | None = None
    endpoints: dict[str, str] = field(default_factory=dict)
    gates: dict[str, str] = field(default_factory=dict)
    tool_belt: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # Keep payloads small: omit empty optional maps / null host_id.
        if not data.get("host_id"):
            data.pop("host_id", None)
        if not data.get("endpoints"):
            data.pop("endpoints", None)
        if not data.get("gates"):
            data.pop("gates", None)
        if not data.get("tool_belt"):
            data.pop("tool_belt", None)
        return data


def _devhost_endpoints() -> dict[str, str]:
    return {
        "resource_sentinel": "http://192.168.5.215:8800",
        "launcher_registry": "/var/www/html/launcher",
        "agent_communication": "mcp://agent-communication",
    }


def _devhost_gates() -> dict[str, str]:
    return {
        "heavy_work": "Call Resource Sentinel recommend_execution_host then request_execution_slot on the chosen host before heavy fan-out.",
        "remote_hermes": "submit_task with approval_required=true and sentinel_lease_id from the peer Sentinel; worker will not run Hermes until approve_task.",
    }


def _tool_belt_summary() -> dict[str, Any]:
    return {
        "mode": "dynamic_proxy_summary",
        "note": "Publish server roles only; activate tools via DynamicMCPProxy / task hint — do not dump full tool schemas in the card.",
        "server_roles": [
            "resource_sentinel:admission",
            "launcher_registry:projects-ports",
            "agent_communication:mailbox-tasks",
            "hermes:cli-worker-gated",
        ],
    }


class AgentDirectory:
    def __init__(self, cards: list[AgentCard]):
        self.cards = {card.id: card for card in cards}

    @classmethod
    def default(cls) -> "AgentDirectory":
        return cls(
            [
                AgentCard(
                    id="server-agent",
                    name="Server Agent",
                    description="LAN/server operations agent for nginx, docker, services, logs, and /var/www-scoped work.",
                    endpoint="mcp://agent-communication/server-agent",
                    capabilities=["services", "nginx", "docker", "logs", "server-artifacts"],
                    scopes=[
                        "registry:read",
                        "project_context:read",
                        "artifact:*",
                        "mailbox:*",
                        "task:*",
                        "fs:read:server:*",
                    ],
                    auth={"scheme": "bearer", "token_env": "AGENT_COMM_SERVER_TOKEN"},
                ),
                AgentCard(
                    id="dev-agent",
                    name="Dev Agent",
                    description=(
                        "Development agent for project code, tests, git artifacts, implementation handoffs, "
                        "and launcher registry context. Prefer host-dev-215 for LAN DevHost endpoints."
                    ),
                    endpoint="mcp://agent-communication/dev-agent",
                    capabilities=[
                        "code",
                        "tests",
                        "git",
                        "project-context",
                        "implementation-handoff",
                        "placement-aware-tasks",
                    ],
                    scopes=[
                        "registry:read",
                        "project_context:read",
                        "artifact:*",
                        "mailbox:*",
                        "task:*",
                        "fs:read:project:*",
                    ],
                    auth={"scheme": "bearer", "token_env": "AGENT_COMM_DEV_TOKEN"},
                    gates=_devhost_gates(),
                    tool_belt=_tool_belt_summary(),
                ),
                AgentCard(
                    id="desktop-agent",
                    name="Desktop Agent",
                    description="Desktop/user-session agent for screenshots, Downloads, Obsidian notes, and user-visible artifacts.",
                    endpoint="mcp://agent-communication/desktop-agent",
                    capabilities=["screenshots", "downloads", "obsidian", "desktop-artifacts"],
                    scopes=[
                        "registry:read",
                        "project_context:read",
                        "artifact:*",
                        "mailbox:*",
                        "task:*",
                        "fs:read:desktop:*",
                    ],
                    auth={"scheme": "bearer", "token_env": "AGENT_COMM_DESKTOP_TOKEN"},
                ),
                AgentCard(
                    id="host-dev-215",
                    name="DevHost stephen-firewall",
                    description=(
                        "LAN DevHost capability card for 192.168.5.215: Sentinel peer, live launcher registry, "
                        "Agent Communication mailbox/tasks, and gated Hermes worker. Does not dump full MCP tool schemas."
                    ),
                    endpoint="mcp://agent-communication/host-dev-215",
                    capabilities=[
                        "placement-peer",
                        "project-registry",
                        "mailbox-tasks",
                        "hermes-worker-gated",
                        "code",
                        "tests",
                        "git",
                        "project-context",
                    ],
                    scopes=[
                        "registry:read",
                        "project_context:read",
                        "artifact:*",
                        "mailbox:*",
                        "task:*",
                        "fs:read:project:*",
                    ],
                    auth={"scheme": "bearer", "token_env": "AGENT_COMM_DEV_TOKEN"},
                    host_id="dev-215",
                    endpoints=_devhost_endpoints(),
                    gates=_devhost_gates(),
                    tool_belt=_tool_belt_summary(),
                ),
            ]
        )

    def list_agents(self) -> list[dict[str, Any]]:
        return [card.to_dict() for card in self.cards.values()]

    def get_agent_card(self, agent_id: str) -> dict[str, Any]:
        if agent_id not in self.cards:
            raise KeyError(f"unknown agent: {agent_id}")
        return self.cards[agent_id].to_dict()
