# Hermes MCP — agent_communication (stdio)

Add to `~/.hermes/config.yaml` (or `hermes config set`):

```yaml
mcp_servers:
  agent_communication:
    command: /home/stephen/projects/agent-communication-mcp/.venv/bin/python
    args:
      - /home/stephen/projects/agent-communication-mcp/scripts/run_stdio.py
    enabled: true
    timeout: 120
    connect_timeout: 60
    env:
      AGENT_CLI_PROFILES_DIR: /home/stephen/projects/ai-agent-teamwork-prompt/profiles
      LAUNCHER_REGISTRY_PATH: /home/stephen/projects/launcher-project-registry/registry.json
```

One-time venv:

```bash
cd ~/projects/agent-communication-mcp && uv venv && uv pip install -e ".[dev]"
```

Verify: `hermes mcp test agent_communication` (18 tools). New CLI sessions need `/reload-mcp` or restart.

HTTP mode (LAN): `scripts/run_http.py` on port 8767 with bearer tokens from `AGENT_COMM_TOKENS_JSON`.