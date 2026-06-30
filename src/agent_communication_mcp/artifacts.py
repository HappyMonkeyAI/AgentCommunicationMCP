from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


class ArtifactStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _task_dir(self, task_id: str) -> Path:
        path = self.root / _safe_component(task_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _metadata_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / "artifacts.json"

    def _load_metadata(self, task_id: str) -> list[dict[str, Any]]:
        path = self._metadata_path(task_id)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_metadata(self, task_id: str, records: list[dict[str, Any]]) -> None:
        path = self._metadata_path(task_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)

    def publish_content(self, task_id: str, name: str, content: str) -> dict[str, Any]:
        safe_name = _safe_component(name)
        artifact_id = uuid.uuid4().hex
        data = content.encode("utf-8")
        sha = hashlib.sha256(data).hexdigest()
        rel = f"{artifact_id}-{safe_name}"
        path = self._task_dir(task_id) / rel
        path.write_bytes(data)
        record = {
            "artifact_id": artifact_id,
            "task_id": task_id,
            "name": safe_name,
            "path": str(path),
            "sha256": sha,
            "bytes": len(data),
            "created_at": _now(),
        }
        records = self._load_metadata(task_id)
        records.append(record)
        self._save_metadata(task_id, records)
        return record

    def list_artifacts(self, task_id: str) -> list[dict[str, Any]]:
        return self._load_metadata(task_id)

    def read_artifact(self, artifact_id: str) -> dict[str, Any]:
        for metadata in self.root.glob("*/artifacts.json"):
            for record in json.loads(metadata.read_text(encoding="utf-8")):
                if record.get("artifact_id") == artifact_id:
                    path = Path(record["path"])
                    return {**record, "content": path.read_text(encoding="utf-8", errors="replace")}
        raise KeyError(f"artifact not found: {artifact_id}")


def _safe_component(value: str) -> str:
    if not value or "/" in value or "\\" in value or value in {".", ".."} or not _SAFE_NAME.match(value):
        raise ValueError(f"unsafe path component: {value!r}")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
