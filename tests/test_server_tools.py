import pytest
from fastmcp.server.context import _current_transport
from agent_communication_mcp.server import health, list_agents, get_agent_card


@pytest.fixture(autouse=True)
def set_stdio_transport():
    token = _current_transport.set("stdio")
    yield
    _current_transport.reset(token)


def test_health_reports_service_ready():
    result = health()

    assert result["service"] == "agent-communication-mcp"
    assert result["status"] in {"planning", "ok"}


def test_agent_tools_are_callable_directly():
    agents = list_agents()
    card = get_agent_card("dev-agent")

    assert agents["count"] >= 3
    assert card["agent"]["id"] == "dev-agent"
