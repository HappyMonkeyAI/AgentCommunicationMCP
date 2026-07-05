#!/usr/bin/env python3
"""Stdio MCP entry for Hermes mcp_servers."""
from agent_communication_mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")