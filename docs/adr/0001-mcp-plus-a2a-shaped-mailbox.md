# ADR 0001 — MCP tools plus A2A-shaped mailbox first

## Status

Proposed

## Context

Stephen wants communication between local network stack agents: server, dev, and desktop. The idea started as a filesystem MCP server leaning on launcher-project-registry and evolved into whether to build A2A services.

Research signals:

- MCP is the right vertical layer for tools/data/files exposed to an agent.
- A2A is the right horizontal layer for discovery, delegation, task state, and artifacts between agents.
- Official MCP authorization guidance emphasizes OAuth 2.1-style authorization for sensitive resources and operations.
- MCP filesystem roots help clients and servers discuss filesystem boundaries, but server-side path enforcement is still required.
- Google A2A highlights Agent Cards, enterprise-grade authentication/authorization, and long-running task state updates.

## Decision

Implement a single `agent-communication-mcp` service first:

1. FastMCP HTTP/StreamableHTTP server with gateway-style bearer auth.
2. Launcher registry adapter for project metadata and context reads.
3. Scoped filesystem/artifact tools limited to named project/agent scopes.
4. A2A-shaped agent cards and task mailbox inside MCP tools.
5. Official A2A protocol compatibility is a later phase, after mailbox semantics stabilize.

## Consequences

- Lower initial complexity than running separate A2A services for every agent.
- Still keeps the model aligned with A2A concepts: agent cards, capabilities, tasks, status, artifacts.
- Easier to test from Hermes via MCP before introducing another protocol client.
- Must be careful not to let "filesystem MCP" become broad disk access.
