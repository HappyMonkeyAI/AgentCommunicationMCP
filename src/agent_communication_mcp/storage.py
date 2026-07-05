from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteStore:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    artifacts_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    instructions TEXT NOT NULL,
                    project_slug TEXT,
                    artifacts_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    preferred_cli_profile TEXT
                );
                CREATE TABLE IF NOT EXISTS task_events (
                    event_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                );
                """
            )
            self._migrate_tasks(conn)

    def _migrate_tasks(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "preferred_cli_profile" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN preferred_cli_profile TEXT")

    def insert_message(self, record: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                (record["message_id"], record["agent_id"], record["subject"], record["body"], json.dumps(record["artifacts"]), record["created_at"]),
            )

    def list_messages(self, agent_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM messages WHERE agent_id = ? ORDER BY created_at", (agent_id,)).fetchall()
        return [_message_from_row(row) for row in rows]

    def insert_task(self, record: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record["task_id"],
                    record["agent_id"],
                    record["title"],
                    record["instructions"],
                    record.get("project_slug"),
                    json.dumps(record["artifacts"]),
                    record["state"],
                    record["created_at"],
                    record["updated_at"],
                    record.get("preferred_cli_profile"),
                ),
            )

    def update_task_state(self, task_id: str, state: str, updated_at: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE tasks SET state = ?, updated_at = ? WHERE task_id = ?", (state, updated_at, task_id))

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        return _task_from_row(row) if row else None

    def list_tasks(self, agent_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM tasks WHERE agent_id = ? ORDER BY created_at", (agent_id,)).fetchall()
        return [_task_from_row(row) for row in rows]

    def insert_event(self, record: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO task_events VALUES (?, ?, ?, ?, ?)",
                (record["event_id"], record["task_id"], record["state"], record["message"], record["created_at"]),
            )

    def list_events(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM task_events WHERE task_id = ? ORDER BY created_at", (task_id,)).fetchall()
        return [dict(row) for row in rows]


def _message_from_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["artifacts"] = json.loads(data.pop("artifacts_json"))
    return data


def _task_from_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["artifacts"] = json.loads(data.pop("artifacts_json"))
    return data
