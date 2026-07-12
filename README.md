# Agent Communication MCP

Authenticated LAN coordination layer for Stephen's server, dev, and desktop agents.

This repo is a planning/bootstrap workspace for a FastMCP server that combines:

- launcher-project-registry-backed project/context discovery
- scoped filesystem and artifact exchange tools
- A2A-shaped agent cards, task mailbox, and task lifecycle
- gateway-style authentication and per-agent authorization scopes

Created: 2026-06-30T19:47:07Z

## Current status

Fully implemented and verified. The FastMCP coordination server has auth gates, scopes, sandboxing, normalized CLI-provider readiness, and bounded control-center activity projections wired up.

## Read-only readiness and control-center tools

Canonical provider metadata is loaded from `~/projects/ai-agent-teamwork-prompt/profiles/` (or `AGENT_CLI_PROFILES_DIR`). Readiness responses expose only stable IDs, display names, binary availability, one of `unavailable`, `authentication-needed`, `ready`, or `degraded`, capabilities, redacted diagnostics, and a UTC check timestamp. Credential files are checked for existence only; secret values and environment contents are never returned.

- `get_provider_readiness(profile_id)` — normalized readiness for one provider.
- `list_provider_readiness()` — readiness for every canonical profile.
- `list_activity(limit=None)` — deterministic newest-first task-event projection with task/agent/project references, approval status, and artifact references.
- `get_control_center(limit=None)` — provider readiness, bounded activity, and aggregate counts.

Activity defaults to 50 records and is capped at 200. Configure these bounds with `AGENT_COMM_ACTIVITY_DEFAULT_LIMIT` and `AGENT_COMM_ACTIVITY_MAX_LIMIT`; requested limits outside `1..max` are rejected.

## Research inputs

- Article MCP saved brief: `/home/stephen/research/agent-communication-mcp/ARTICLE_BRIEF.md`
- Local research handoff: `research/RESEARCH.md`
- First ADR: `docs/adr/0001-mcp-plus-a2a-shaped-mailbox.md`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
