"""Database connection adapter.

Provides a unified connection interface for both SQLite (local development)
and PostgreSQL/Layerbase (production). The connection wrapper converts
SQLite-style ``?`` parameter placeholders to PostgreSQL-style ``%s`` so that
existing SQL queries work unchanged with psycopg.

Usage:
    from app.core.db import get_db_connection, db_exists

    conn = get_db_connection()
    cur = conn.execute("SELECT * FROM observations WHERE parameter = ?", ("pm25",))
    rows = cur.fetchall()
    conn.close()

    # Read-only (SQLite WAL mode, or plain PostgreSQL):
    conn = get_db_connection(read_only=True)

    # Check if DB is accessible (file check for SQLite, always True for cloud):
    if not db_exists():
        return {"status": "unavailable"}

Environment:
    LAYERBASE_DB_URL — PostgreSQL connection string for Layerbase.
    When set, production mode is active (psycopg-backed).
    When unset, falls back to SQLite (local development).
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from loguru import logger

# ── PostgreSQL check ───────────────────────────────────────────────────
_LAYERBASE_URL: str | None = os.environ.get("LAYERBASE_DB_URL")


def is_cloud_db() -> bool:
    """Return True if LAYERBASE_DB_URL is set (production mode)."""
    if _LAYERBASE_URL:
        return True
    try:
        from .config import get_settings
        settings = get_settings()
        return bool(settings.layerbase_db_url)
    except Exception:
        return False


def _get_cloud_url() -> str:
    """Get the Layerbase connection URL."""
    if _LAYERBASE_URL:
        return _LAYERBASE_URL
    from .config import get_settings
    settings = get_settings()
    if settings.layerbase_db_url:
        return settings.layerbase_db_url
    raise RuntimeError("No Layerbase DB URL configured")


def _resolve_sqlite_path() -> Path:
    """Resolve SQLite database path from LPA_DATABASE_URL or default."""
    from .config import get_settings
    settings = get_settings()
    raw = settings.database_url.replace("sqlite:///", "")
    path = Path(raw)
    if not path.is_absolute():
        backend_root = Path(__file__).resolve().parent.parent.parent
        path = backend_root / path
    return path


def db_exists() -> bool:
    """Check if the database is accessible (file exists for SQLite, always True for cloud)."""
    if is_cloud_db():
        return True
    return _resolve_sqlite_path().exists()


# ── Psycopg wrapper (presents sqlite3-like API) ───────────────────────


class _Row:
    """Lightweight sqlite3.Row-compatible object for psycopg rows.

    Supports both index-based and key-based access:
        row[0]         — by column index
        row["name"]    — by column name
        row.keys()     — list of column names
    """

    __slots__ = ("_values", "_names")

    def __init__(self, names: tuple[str, ...], values: tuple) -> None:
        self._names = names
        self._values = values

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        if isinstance(key, str):
            idx = self._names.index(key)
            return self._values[idx]
        raise TypeError(f"Row indices must be integers or strings, not {type(key)}")

    def keys(self) -> list[str]:
        return list(self._names)

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __eq__(self, other):
        if isinstance(other, tuple):
            return self._values == other
        return NotImplemented

    def __repr__(self):
        return f"_Row({dict(zip(self._names, self._values))})"


class _PsycopgCursor:
    """Thin wrapper around psycopg.Cursor that mimics sqlite3.Cursor.

    Returns _Row objects when the connection's row_factory is sqlite3.Row,
    making it compatible with code that does ``row["column_name"]``.
    """

    def __init__(self, cursor, row_factory=None) -> None:
        self._cur = cursor
        self._row_factory = row_factory

    def _wrap_row(self, row):
        if row is None:
            return None
        if self._row_factory is not None and self._cur.description:
            names = tuple(desc[0] for desc in self._cur.description)
            return _Row(names, tuple(row))
        return tuple(row)

    def fetchone(self):
        return self._wrap_row(self._cur.fetchone())

    def fetchall(self):
        return [self._wrap_row(r) for r in self._cur.fetchall()]

    def fetchmany(self, size: int):
        return [self._wrap_row(r) for r in self._cur.fetchmany(size)]

    @property
    def description(self):
        return self._cur.description

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self) -> None:
        self._cur.close()


# PRAGMA keywords that PostgreSQL doesn't support (silently ignored).
_PRAGMA_RE = re.compile(r"^\s*PRAGMA\b", re.IGNORECASE)


class _PsycopgConnection:
    """Thin wrapper around psycopg.Connection that mimics sqlite3.Connection.

    Key adaptations:
    - Converts SQLite-style ``?`` placeholders to PostgreSQL ``%s``.
    - Silently ignores PRAGMA statements (PostgreSQL doesn't support them).
    - Silently ignores sqlite_master queries (returns empty cursor).
    - Returns _Row objects when row_factory is set to sqlite3.Row.
    """

    _QMARK_RE = re.compile(r"(?<!\?)\?")

    def __init__(self, conn, row_factory=None) -> None:
        self._conn = conn
        self._row_factory = row_factory

    @property
    def row_factory(self):
        return self._row_factory

    @row_factory.setter
    def row_factory(self, value) -> None:
        self._row_factory = value

    def _convert(self, sql: str) -> str:
        """Convert ``?`` placeholders to ``%s``."""
        return self._QMARK_RE.sub("%s", sql)

    def execute(self, sql: str, params=None):
        # Silently ignore PRAGMA statements
        if _PRAGMA_RE.match(sql):
            return _PsycopgCursor(self._conn.cursor(), self._row_factory)
        # Silently ignore sqlite_master queries — return empty result
        if "sqlite_master" in sql.lower():
            return _PsycopgCursor(self._conn.cursor(), self._row_factory)
        cur = self._conn.cursor()
        if params is not None:
            cur.execute(self._convert(sql), params)
        else:
            cur.execute(sql)
        return _PsycopgCursor(cur, self._row_factory)

    def executemany(self, sql: str, params_seq):
        cur = self._conn.cursor()
        cur.executemany(self._convert(sql), params_seq)
        return _PsycopgCursor(cur, self._row_factory)

    def executescript(self, script: str) -> None:
        """Execute multiple statements. Silently skips PRAGMA and sqlite_master."""
        for stmt in script.split(";"):
            stmt = stmt.strip()
            if not stmt or stmt.startswith("--"):
                continue
            if _PRAGMA_RE.match(stmt):
                continue
            try:
                self._conn.cursor().execute(stmt)
            except Exception as exc:
                logger.debug(f"executescript skipped: {exc}")

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    @property
    def autocommit(self):
        return self._conn.autocommit

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        self._conn.autocommit = value


# ── Factory ────────────────────────────────────────────────────────────


def get_db_connection(
    read_only: bool = False,
    row_factory: Any = None,
    db_path: str | Path | None = None,
) -> sqlite3.Connection | _PsycopgConnection:
    """Get a database connection — SQLite locally, PostgreSQL in production.

    Args:
        read_only: Hint for SQLite (read-only URI mode). Ignored for PostgreSQL.
        row_factory: Set to ``sqlite3.Row`` for dict-style row access.
                     Always set for SQLite; needed explicitly for psycopg.
        db_path: Optional explicit path to an SQLite database file.
                 When set and not in cloud mode, connects to this specific
                 file instead of the default database. Ignored for PostgreSQL.

    Returns:
        A connection object that supports sqlite3-style execute/fetch/close.
    """
    if is_cloud_db():
        import psycopg

        url = _get_cloud_url()
        conn = psycopg.connect(
            url,
            autocommit=True,
        )
        logger.debug("Connected to Layerbase (PostgreSQL wire protocol)")
        return _PsycopgConnection(conn, row_factory=row_factory)

    # ── SQLite fallback ────────────────────────────────────────────────
    if db_path is None:
        db_path = _resolve_sqlite_path()
    elif isinstance(db_path, str):
        db_path = Path(db_path)

    if read_only and db_path.exists():
        conn = sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            timeout=10,
        )
    else:
        conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = row_factory or sqlite3.Row
    return conn


def get_db_path() -> Path:
    """Return the SQLite database file path (used for file-based checks)."""
    return _resolve_sqlite_path()
