# AGENTS — agent-communication-mcp

Follow `CONTEXT.md` first.

## Safety rules

- No arbitrary filesystem exposure. Resolve all filesystem tools through launcher registry project roots or named artifact roots.
- Do not store secrets in this repo or launcher-project-registry.
- Prefer read-only operations until auth, scopes, and audit logging are tested.
- Use FastMCP tests/CLI before registering with Hermes.
- Keep A2A official-protocol compatibility as a later phase; first build MCP-native agent cards and mailbox.

## Verification

- Run `uv run --extra dev pytest -q` after changes.
- For HTTP server work, probe unauthenticated and authenticated paths.
