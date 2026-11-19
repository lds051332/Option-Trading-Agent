"""Same-day cache for the news scout, shared by the web desk and the Finch runtime.

Both run as separate processes on one host, so the cache lives in SQLite on disk.
Keys carry the US/Eastern trading date: a new session starts with fresh searches.
Set OPTION_DESK_SCOUT_CACHE=off to disable, or to a file path to relocate it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

RETENTION_SECONDS = 3 * 24 * 3600

_lock = threading.Lock()
_conns: dict[str, sqlite3.Connection] = {}


def market_day() -> date:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:
        return datetime.now(timezone.utc).date()


def _path() -> Path | None:
    raw = (os.environ.get("OPTION_DESK_SCOUT_CACHE") or "").strip()
    if raw.lower() in {"off", "0", "false", "none"}:
        return None
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".option_desk" / "scout_cache.sqlite3"


def _connect(path: Path) -> sqlite3.Connection:
    key = str(path)
    conn = _conns.get(key)
    if conn is not None:
        return conn
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(key, check_same_thread=False, isolation_level=None, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scout_cache ("
        "key TEXT PRIMARY KEY, value TEXT NOT NULL, created_at REAL NOT NULL)"
    )
    conn.execute("DELETE FROM scout_cache WHERE created_at < ?", (time.time() - RETENTION_SECONDS,))
    _conns[key] = conn
    return conn


def cache_key(kind: str, *parts: object) -> str:
    blob = json.dumps([kind, *[str(p) for p in parts]], ensure_ascii=False)
    return f"{kind}:{hashlib.sha256(blob.encode('utf-8')).hexdigest()}"


def get(key: str) -> Any | None:
    path = _path()
    if path is None:
        return None
    try:
        with _lock:
            row = _connect(path).execute(
                "SELECT value FROM scout_cache WHERE key = ?", (key,)
            ).fetchone()
    except sqlite3.Error:
        return None
    return json.loads(row[0]) if row else None


def put(key: str, value: Any) -> None:
    path = _path()
    if path is None:
        return
    try:
        with _lock:
            _connect(path).execute(
                "INSERT OR REPLACE INTO scout_cache (key, value, created_at) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False), time.time()),
            )
    except sqlite3.Error:
        return
