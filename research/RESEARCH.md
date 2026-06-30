# Agent Communication MCP — Research Handoff

## Working thesis

Build one authenticated MCP service first, not a full autonomous agent mesh. Use MCP for the safe tool/data/filesystem surface and A2A concepts for peer-agent discovery/task lifecycle.

## Evidence gathered

### Article MCP

Saved article brief: `/home/stephen/research/agent-communication-mcp/ARTICLE_BRIEF.md`.

Key signals:

- MCP and A2A are complementary: MCP = vertical tools/data, A2A = horizontal agent delegation.
- Production MCP should start with narrow/read-only operational access where possible.
- Filesystem MCP is useful but risky if configured too broadly.
- Structured tool/action metadata reduces scraping/guessing.
- Authorization is a core production concern, not a later wrapper.

### Official/primary docs checked

- MCP Authorization docs were reachable and state that MCP authorization protects sensitive resources/operations and uses standardized authorization flows; the page explicitly references OAuth 2.1.
- MCP Roots spec was reachable and describes filesystem roots as boundaries clients expose to servers.
- MCP Transports docs were reachable and cover stdio and Streamable HTTP.
- Google A2A announcement was reachable and describes capability discovery via Agent Cards, enterprise-grade authentication/authorization, long-running tasks, feedback/notifications/state updates, and modality-agnostic exchange.
- A2A project docs were reachable and expose quickstart material around agent skills, agent cards, agent executors, streaming, and multiturn workflows.

## Recommended architecture

```text
Hermes / local agents
        |
        v
MCP Gateway/auth pattern
        |
        v
agent-communication-mcp
  |-- launcher registry adapter
  |-- scoped filesystem/artifact tools
  |-- agent cards
  |-- task mailbox/lifecycle
  |-- audit log
        |
        +--> server-agent
        +--> dev-agent
        +--> desktop-agent
```

## Deep research lenses to run next

1. Technical — FastMCP auth/middleware, StreamableHTTP, path canonicalization, SQLite vs JSON store.
2. Security — bearer vs OAuth/OIDC, per-agent scopes, audit logs, artifact signing/hashes.
3. Product — smallest useful tool surface for Stephen's workflows.
4. Strategic — whether to implement official A2A compatibility or stay MCP-native.
5. Operational — deployment under existing gateway/nginx, port allocation via launcher registry.
6. Contrarian — why not just use shared folders/git/issues/OpenProject instead?
7. Historical — lessons from agent meshes/message buses that became too complex.
8. Customer/user — which handoffs Stephen actually repeats between agents.
9. First-principles — minimum primitives: identity, capability, message, task, artifact, scope.

## Open questions

- Does Stephen want this reachable from all LAN hosts immediately, or only localhost behind gateway first?
- Should `server-agent`, `dev-agent`, and `desktop-agent` be logical identities in one Hermes process or separately deployed services?
- What current MCP gateway auth code/config can be reused directly?
- Should the mailbox persist in SQLite to support concurrent agents, or JSON for simpler inspection?
- Which filesystem scopes are safe to enable on day one?
