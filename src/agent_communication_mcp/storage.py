from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
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
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, subject TEXT NOT NULL,
                    body TEXT NOT NULL, artifacts_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, title TEXT NOT NULL,
                    instructions TEXT NOT NULL, project_slug TEXT, artifacts_json TEXT NOT NULL,
                    state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    preferred_cli_profile TEXT, lease_owner TEXT, lease_expires_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, max_attempts INTEGER NOT NULL DEFAULT 3
                );
                CREATE TABLE IF NOT EXISTS task_events (
                    event_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, state TEXT NOT NULL,
                    message TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                );
            """)
            self._migrate_tasks(conn)

    def _migrate_tasks(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        migrations = {
            "preferred_cli_profile": "ALTER TABLE tasks ADD COLUMN preferred_cli_profile TEXT",
            "lease_owner": "ALTER TABLE tasks ADD COLUMN lease_owner TEXT",
            "lease_expires_at": "ALTER TABLE tasks ADD COLUMN lease_expires_at TEXT",
            "attempts": "ALTER TABLE tasks ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0",
            "last_error": "ALTER TABLE tasks ADD COLUMN last_error TEXT",
            "max_attempts": "ALTER TABLE tasks ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 3",
        }
        for name, statement in migrations.items():
            if name not in cols:
                conn.execute(statement)

    def _connect_and(self):
        return self._connect()

    def insert_message(self, record: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                (record["message_id"], record["agent_id"], record["subject"], record["body"], json.dumps(record["artifacts"]), record["created_at"]))

    def list_messages(self, agent_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM messages WHERE agent_id = ? ORDER BY created_at", (agent_id,)).fetchall()
        return [_message_from_row(row) for row in rows]

    def insert_task(self, record: dict[str, Any]) -> None:
        values = (record["task_id"], record["agent_id"], record["title"], record["instructions"], record.get("project_slug"), json.dumps(record["artifacts"]), record["state"], record["created_at"], record["updated_at"], record.get("preferred_cli_profile"), record.get("lease_owner"), record.get("lease_expires_at"), record.get("attempts", 0), record.get("last_error"), record.get("max_attempts", 3))
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, agent_id, title, instructions, project_slug, artifacts_json, state, created_at, updated_at, preferred_cli_profile, lease_owner, lease_expires_at, attempts, last_error, max_attempts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                values,
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

    def claim_task(self, owner: str, lease_seconds: int = 300, now: str | None = None) -> dict[str, Any] | None:
        now = now or _now()
        expires = _add_seconds(now, lease_seconds)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""SELECT * FROM tasks WHERE
                (state = 'submitted' AND attempts < max_attempts)
                OR (state = 'working' AND lease_expires_at IS NOT NULL AND lease_expires_at <= ? AND attempts < max_attempts)
                ORDER BY created_at, task_id LIMIT 1""", (now,)).fetchone()
            if row is None:
                conn.execute("UPDATE tasks SET state='failed', last_error='maximum attempts exceeded', updated_at=? WHERE (state='submitted' OR state='working') AND attempts >= max_attempts AND (state='submitted' OR lease_expires_at IS NULL OR lease_expires_at <= ?)", (now, now))
                conn.commit()
                return None
            conn.execute("""UPDATE tasks SET state='working', lease_owner=?, lease_expires_at=?,
                attempts=attempts+1, updated_at=? WHERE task_id=?""", (owner, expires, now, row["task_id"]))
            claimed = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (row["task_id"],)).fetchone()
            conn.commit()
        return _task_from_row(claimed)

    def set_task_lease(self, task_id: str, owner: str, lease_expires_at: str | None, last_error: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE tasks SET lease_expires_at=?, last_error=?, updated_at=? WHERE task_id=? AND lease_owner=?", (lease_expires_at, last_error, _now(), task_id, owner))

    def finish_task(self, task_id: str, owner: str, state: str, message: str, last_error: str | None = None) -> bool:
        now = _now()
        with self._connect() as conn:
            updated = conn.execute("""UPDATE tasks SET state=?, lease_owner=NULL, lease_expires_at=NULL,
                last_error=?, updated_at=? WHERE task_id=? AND lease_owner=?""", (state, last_error, now, task_id, owner)).rowcount
            if updated:
                conn.execute("INSERT INTO task_events VALUES (?, ?, ?, ?, ?)", (__import__("uuid").uuid4().hex, task_id, state, message, now))
            return bool(updated)

    def insert_event(self, record: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO task_events VALUES (?, ?, ?, ?, ?)", (record["event_id"], record["task_id"], record["state"], record["message"], record["created_at"]))

    def list_events(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM task_events WHERE task_id = ? ORDER BY created_at", (task_id,)).fetchall()
        return [dict(row) for row in rows]

    def list_activity_events(self, limit: int, agent_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            query = "SELECT e.event_id, e.task_id, e.state, e.message, e.created_at, t.agent_id, t.project_slug, t.artifacts_json FROM task_events AS e JOIN tasks AS t ON t.task_id = e.task_id"
            params: tuple[Any, ...]
            if agent_id is None:
                params = (limit,)
            else:
                query += " WHERE t.agent_id = ?"
                params = (agent_id, limit)
            query += " ORDER BY e.created_at DESC, e.event_id DESC LIMIT ?"
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def _add_seconds(value: str, seconds: int) -> str:
    return (datetime.fromisoformat(value.replace("Z", "+00:00")) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _message_from_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row); data["artifacts"] = json.loads(data.pop("artifacts_json")); return data


def _task_from_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row); data["artifacts"] = json.loads(data.pop("artifacts_json")); return data
