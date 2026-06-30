from agent_communication_mcp.server import health


def test_health_planning_status():
    assert health()["status"] == "planning"
