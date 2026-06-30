"""Placeholder server module for the implementation plan.

Do not deploy yet. See docs/plans/IMPLEMENTATION_PLAN.md.
"""

try:
    from fastmcp import FastMCP
except Exception:  # pragma: no cover - dependency not installed during planning
    FastMCP = None

mcp = FastMCP("Agent Communication MCP") if FastMCP else None


def health() -> dict:
    """Return static planning-stage health."""
    return {"status": "planning", "service": "agent-communication-mcp"}
