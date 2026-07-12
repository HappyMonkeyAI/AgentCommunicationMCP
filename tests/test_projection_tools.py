import asyncio
from unittest.mock import patch

import pytest
from fastmcp.server.context import _current_transport

from agent_communication_mcp.auth import Identity
from agent_communication_mcp.server import (
    get_control_center,
    get_provider_readiness,
    list_activity,
    list_provider_readiness,
    mcp,
)


@pytest.fixture(autouse=True)
def set_stdio_transport():
    token = _current_transport.set("stdio")
    yield
    _current_transport.reset(token)


def test_read_only_projection_tools_delegate_to_services():
    with patch("agent_communication_mcp.server._providers") as providers, patch(
        "agent_communication_mcp.server._activity"
    ) as activity:
        providers.get.return_value = {"id": "codex", "state": "ready"}
        providers.list.return_value = [{"id": "codex", "state": "ready"}]
        activity.list.return_value = {"activities": [], "count": 0}
        activity.control_center.return_value = {"providers": [], "activity": {"activities": []}}

        assert get_provider_readiness("codex")["id"] == "codex"
        assert list_provider_readiness()["count"] == 1
        assert list_activity(limit=7)["count"] == 0
        assert get_control_center(limit=9)["activity"]["activities"] == []
        activity.list.assert_called_once_with(7, agent_id=None)
        activity.control_center.assert_called_once_with(9)


def test_list_activity_scopes_non_admin_identity_to_own_events():
    identity = Identity(agent_id="dev-agent", scopes={"mailbox:read"}, claims={})
    with patch("agent_communication_mcp.server.check_mcp_auth_and_scope", return_value=identity), patch(
        "agent_communication_mcp.server._activity"
    ) as activity:
        activity.list.return_value = {"activities": [], "count": 0}

        list_activity(limit=5)

        activity.list.assert_called_once_with(5, agent_id="dev-agent")


def test_projection_tools_are_registered_with_fastmcp():
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}

    assert {
        "get_provider_readiness",
        "list_provider_readiness",
        "list_activity",
        "get_control_center",
    }.issubset(names)
