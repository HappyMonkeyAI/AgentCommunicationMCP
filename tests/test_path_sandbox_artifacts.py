import pytest

from agent_communication_mcp.path_sandbox import PathSandbox, PathSandboxError
from agent_communication_mcp.artifacts import ArtifactStore


def test_path_sandbox_allows_relative_path_under_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "file.txt").write_text("hello", encoding="utf-8")
    sandbox = PathSandbox({"scope": root})

    assert sandbox.resolve("scope", "file.txt") == (root / "file.txt").resolve()


def test_path_sandbox_rejects_parent_traversal(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    sandbox = PathSandbox({"scope": root})

    with pytest.raises(PathSandboxError):
        sandbox.resolve("scope", "../outside.txt")


def test_path_sandbox_rejects_symlink_escape(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    sandbox = PathSandbox({"scope": root})

    with pytest.raises(PathSandboxError):
        sandbox.resolve("scope", "link/secret.txt")


def test_artifact_store_writes_and_reads_content_under_root(tmp_path):
    store = ArtifactStore(tmp_path / "artifacts")

    artifact = store.publish_content("task-1", "note.txt", "hello")

    assert artifact["task_id"] == "task-1"
    assert artifact["sha256"]
    assert store.read_artifact(artifact["artifact_id"])["content"] == "hello"
    assert len(store.list_artifacts("task-1")) == 1


def test_artifact_store_rejects_pathlike_names(tmp_path):
    store = ArtifactStore(tmp_path / "artifacts")

    with pytest.raises(ValueError):
        store.publish_content("task-1", "../bad.txt", "hello")
