#!/usr/bin/env python3
from agent_communication_mcp.server import mcp
import os

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host=os.getenv("AGENT_COMM_HOST", "127.0.0.1"),
        port=int(os.getenv("AGENT_COMM_PORT", "8767")),
    )
