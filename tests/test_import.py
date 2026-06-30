from agent_communication_mcp.server import health


def test_health_status():
    assert health()["status"] == "ok"
