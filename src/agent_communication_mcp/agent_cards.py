from __future__ import annotations

from dataclasses import dataclass, asdict
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentDirectory:
    def __init__(self, cards: list[AgentCard]):
        self.cards = {card.id: card for card in cards}

    @classmethod
    def default(cls) -> "AgentDirectory":
        return cls([
            AgentCard(
                id="server-agent",
                name="Server Agent",
                description="LAN/server operations agent for nginx, docker, services, logs, and /var/www-scoped work.",
                endpoint="mcp://agent-communication/server-agent",
                capabilities=["services", "nginx", "docker", "logs", "server-artifacts"],
                scopes=["registry:read", "project_context:read", "artifact:*", "mailbox:*", "task:*", "fs:read:server:*"],
                auth={"scheme": "bearer", "token_env": "AGENT_COMM_SERVER_TOKEN"},
            ),
            AgentCard(
                id="dev-agent",
                name="Dev Agent",
                description="Development agent for project code, tests, git artifacts, implementation handoffs, and launcher registry context.",
                endpoint="mcp://agent-communication/dev-agent",
                capabilities=["code", "tests", "git", "project-context", "implementation-handoff"],
                scopes=["registry:read", "project_context:read", "artifact:*", "mailbox:*", "task:*", "fs:read:project:*"],
                auth={"scheme": "bearer", "token_env": "AGENT_COMM_DEV_TOKEN"},
            ),
            AgentCard(
                id="desktop-agent",
                name="Desktop Agent",
                description="Desktop/user-session agent for screenshots, Downloads, Obsidian notes, and user-visible artifacts.",
                endpoint="mcp://agent-communication/desktop-agent",
                capabilities=["screenshots", "downloads", "obsidian", "desktop-artifacts"],
                scopes=["registry:read", "project_context:read", "artifact:*", "mailbox:*", "task:*", "fs:read:desktop:*"],
                auth={"scheme": "bearer", "token_env": "AGENT_COMM_DESKTOP_TOKEN"},
            ),
        ])

    def list_agents(self) -> list[dict[str, Any]]:
        return [card.to_dict() for card in self.cards.values()]

    def get_agent_card(self, agent_id: str) -> dict[str, Any]:
        if agent_id not in self.cards:
            raise KeyError(f"unknown agent: {agent_id}")
        return self.cards[agent_id].to_dict()
