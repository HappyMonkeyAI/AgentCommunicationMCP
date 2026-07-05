import pytest
from fastmcp.server.context import _current_transport

from agent_communication_mcp.cli_profiles import load_profile, suggest_cli_for_task
from agent_communication_mcp.server import get_cli_profile, list_cli_profiles, suggest_cli_for_task as mcp_suggest


@pytest.fixture(autouse=True)
def set_stdio_transport():
    token = _current_transport.set("stdio")
    yield
    _current_transport.reset(token)


def test_list_cli_profiles_includes_codex():
    result = list_cli_profiles()
    assert "codex" in result["profiles"]
    assert "profiles_dir" in result


def test_get_cli_profile_codex():
    result = get_cli_profile("codex")
    assert result["profile"]["id"] == "codex"
    assert "good_for" in result["profile"]


def test_suggest_plan_implementation_prefers_coding_cli():
    result = suggest_cli_for_task(
        "Read docs/plans/foo.md and implement multi-file adapter modules with pytest"
    )
    top = result["suggested"]
    assert top is not None
    assert top["profile_id"] in {"codex", "agy", "opencode"}


def test_mcp_suggest_wrapper():
    out = mcp_suggest("orchestrate MCP tools and delegate subagents")
    assert out["suggested"]["profile_id"] in {"hermes", "grok", None} or out["suggested"] is None or out["suggested"]["profile_id"] in {
        "hermes",
        "grok",
    }