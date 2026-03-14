"""Postgres database layer for agent configuration persistence."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras

_conn: "psycopg2.connection | None" = None


def _get_conn() -> "psycopg2.connection":
    global _conn
    if _conn is None or _conn.closed:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            msg = "DATABASE_URL environment variable is not set"
            raise RuntimeError(msg)
        _conn = psycopg2.connect(database_url)
        _conn.autocommit = True
    return _conn


def init_db() -> None:
    """Create the agents table if it does not exist."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                model TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def create_agent(agent_id: str, name: str, model: str, system_prompt: str) -> dict[str, Any]:
    conn = _get_conn()
    created_at = datetime.now(timezone.utc).isoformat()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO agents (id, name, model, system_prompt, created_at) VALUES (%s, %s, %s, %s, %s)",
            (agent_id, name, model, system_prompt, created_at),
        )
    return {"id": agent_id, "name": name, "model": model, "system_prompt": system_prompt, "created_at": created_at}


def list_agents() -> list[dict[str, Any]]:
    conn = _get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, name, model, system_prompt, created_at FROM agents ORDER BY created_at")
        return [dict(row) for row in cur.fetchall()]


def get_agent(agent_id: str) -> dict[str, Any] | None:
    conn = _get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, name, model, system_prompt, created_at FROM agents WHERE id = %s", (agent_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_agent(agent_id: str, name: str, model: str, system_prompt: str) -> dict[str, Any] | None:
    conn = _get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "UPDATE agents SET name = %s, model = %s, system_prompt = %s WHERE id = %s RETURNING id, name, model, system_prompt, created_at",
            (name, model, system_prompt, agent_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete_agent(agent_id: str) -> bool:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
        return cur.rowcount > 0
