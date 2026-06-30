# Hermes connection notes

The service runs as a FastMCP StreamableHTTP server.

## Local smoke run

```bash
cd /home/stephen/projects/agent-communication-mcp
PYTHONPATH=src AGENT_COMM_PORT=8767 uv run python scripts/run_http.py
```

Default local URL:

```text
http://127.0.0.1:8767/mcp
```

## Auth

The server uses FastMCP `StaticTokenVerifier` for the first LAN/dev slice. Defaults exist for local development only:

- `dev-token`
- `server-token`
- `desktop-token`

For real deployment, set `AGENT_COMM_TOKENS_JSON` outside the repo, e.g. in the service environment:

```json
{
  "replace-with-long-random-token": {
    "agent_id": "dev-agent",
    "scopes": ["registry:read", "project_context:read", "artifact:read", "artifact:write", "mailbox:read", "mailbox:write", "task:submit", "task:update", "fs:read:project:*"]
  }
}
```

## Hermes MCP config

```bash
hermes config set mcp_servers.agent_communication.url "http://127.0.0.1:8767/mcp"
hermes config set mcp_servers.agent_communication.headers.Authorization "Bearer <real-token>"
hermes config set mcp_servers.agent_communication.timeout 120
hermes config set mcp_servers.agent_communication.connect_timeout 30
```

Restart Hermes/gateway after config changes.

## Verified probes

Unauthenticated reachability fails closed:

```bash
curl http://127.0.0.1:8767/mcp
# HTTP 401
```

Authenticated StreamableHTTP session via MCP SDK:

```python
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
```

Observed locally: `list_tools()` returned 14 tools and `health` returned `status=ok`.
