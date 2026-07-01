# Agent Communication MCP

Authenticated LAN coordination layer for Stephen's server, dev, and desktop agents.

This repo is a planning/bootstrap workspace for a FastMCP server that combines:

- launcher-project-registry-backed project/context discovery
- scoped filesystem and artifact exchange tools
- A2A-shaped agent cards, task mailbox, and task lifecycle
- gateway-style authentication and per-agent authorization scopes

Created: 2026-06-30T19:47:07Z

## Current status

Fully implemented and verified. The FastMCP coordination server has auth gates, scopes, and sandboxing fully wired up. All security verification tests pass.

## Research inputs

- Article MCP saved brief: `/home/stephen/research/agent-communication-mcp/ARTICLE_BRIEF.md`
- Local research handoff: `research/RESEARCH.md`
- First ADR: `docs/adr/0001-mcp-plus-a2a-shaped-mailbox.md`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
