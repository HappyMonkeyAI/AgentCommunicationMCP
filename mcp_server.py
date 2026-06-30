#!/usr/bin/env python3
"""FastMCP CLI entrypoint.

The FastMCP CLI loads file paths as standalone modules, so this wrapper adds
`src/` to sys.path and exports the package server object.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agent_communication_mcp.server import mcp  # noqa: E402
