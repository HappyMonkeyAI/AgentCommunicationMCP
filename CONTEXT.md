# CONTEXT — agent-communication-mcp

Authenticated LAN coordination service for local agents.

## Goal

Build a FastMCP HTTP/StreamableHTTP server that gives local agents safe shared tools for communication and project-aware filesystem access, while keeping launcher-project-registry as the source of truth for project paths, ports, CONTEXT.md, and MCP metadata.

## Intended stack

- Python 3.11+
- FastMCP
- HTTP/StreamableHTTP transport
- bearer token first; OAuth/OIDC-compatible authorization later if exposed beyond LAN
- launcher-project-registry adapter, not a duplicated registry
- JSON files or SQLite for first mailbox/task store

## Non-negotiable rules

1. Do not expose arbitrary filesystem access. All paths must resolve through named scopes and launcher registry project roots.
2. Do not store secrets in launcher-project-registry or this repo.
3. Start read-first: project discovery, context read, message/task read/write. Add broad file writes only after audit logs and scoped authorization are working.
4. Treat MCP roots as helpful boundaries/context, not the only security mechanism. Enforce path allowlists server-side.
5. Use A2A concepts for discovery and task lifecycle, but do not overbuild official A2A compatibility until the simple mailbox proves useful.

## Initial agents

- `server-agent`: nginx, docker/services, `/var/www`, logs; highest risk, narrowest writes.
- `dev-agent`: `~/projects`, tests, git artifacts, implementation handoffs.
- `desktop-agent`: user-session artifacts such as screenshots, Downloads, Obsidian notes; should default read-only until explicit scope grants.

## First tool surface

- `list_agents`
- `get_agent_card`
- `list_projects`
- `get_project_context`
- `resolve_project_workspace`
- `drop_agent_message`
- `list_agent_inbox`
- `submit_task`
- `get_task`
- `append_task_event`
- `publish_artifact`

## Related local projects

- `/home/stephen/projects/launcher-project-registry`
- `/home/stephen/projects/article-research-mcp`
