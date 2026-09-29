"""SQLite locally; PostgreSQL in a private schema when DATABASE_URL is set."""

import json
import re
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from flask import current_app
from .config import DEFAULT

_rollback = ContextVar("tamara_rollback", default=None)
WRITE_LOCK = 84729301
SCHEMA = """
CREATE TABLE IF NOT EXISTS admins(name TEXT PRIMARY KEY, password TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, "user" TEXT, csrf TEXT NOT NULL, expires REAL NOT NULL, seen REAL NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(scope TEXT, created REAL);
CREATE INDEX IF NOT EXISTS attempts_scope ON attempts(scope,created);
CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1), draft TEXT NOT NULL, published TEXT NOT NULL, revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, created REAL NOT NULL, "user" TEXT NOT NULL, action TEXT NOT NULL, content TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY, created REAL NOT NULL, "user" TEXT NOT NULL, width INTEGER, height INTEGER);
CREATE TABLE IF NOT EXISTS panel_records(collection TEXT NOT NULL,id TEXT NOT NULL,data TEXT NOT NULL,version INTEGER NOT NULL,PRIMARY KEY(collection,id));
CREATE TABLE IF NOT EXISTS panel_history(id INTEGER PRIMARY KEY,created REAL NOT NULL,"user" TEXT NOT NULL,collection TEXT NOT NULL,record_id TEXT NOT NULL,previous TEXT NOT NULL);
"""


def db():
    return current_app.db()


def on_rollback(callback):
    callbacks = _rollback.get()
    if callbacks is None:
        raise RuntimeError("La subida necesita una transacción de base de datos.")
    callbacks.append(callback)


class Row(dict):
    """Retain both named and positional access used by the existing SQLite code."""

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return tuple(self.values())[key]
        return super().__getitem__(key)


def row_factory(cursor):
    columns = [c.name for c in cursor.description] if cursor.description else []
    return lambda values: Row(zip(columns, values))


def postgres_sql(sql):
    # Only static application SQL enters here; values remain bound parameters.
    # Preserve quoted strings/identifiers while adapting placeholders and USER.
    tokens = re.split(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\")", sql)
    for i in range(0, len(tokens), 2):
        tokens[i] = re.sub(r"\buser\b", '"user"', tokens[i], flags=re.I).replace(
            "?", "%s"
        )
    return "".join(tokens).replace("ORDER BY rowid", "ORDER BY sort_id")


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        if sql.strip().upper() == "BEGIN IMMEDIATE":
            # Same serialization boundary as SQLite's write transaction.
            return self.connection.execute(
                "SELECT pg_advisory_xact_lock(%s)", (WRITE_LOCK,)
            )
        return self.connection.execute(postgres_sql(sql), params or None)

    def executemany(self, sql, params):
        with self.connection.cursor() as cursor:
            cursor.executemany(postgres_sql(sql), params)


def configure_database(app):
    url = app.config["DATABASE_URL"]
    directory = app.config["DATA_DIR"]
    if not url:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "uploads").mkdir(exist_ok=True)

    @contextmanager
    def connection():
        callbacks = []
        token = _rollback.set(callbacks)
        try:
            if url:
                import psycopg

                try:
                    raw = psycopg.connect(
                        url,
                        connect_timeout=15,
                        sslmode="require",
                        row_factory=row_factory,
                        prepare_threshold=None,
                    )
                except psycopg.Error:
                    raise RuntimeError(
                        "No se pudo conectar a PostgreSQL. Revisa DATABASE_URL y el estado del proyecto."
                    ) from None
                with raw:
                    raw.execute("SET LOCAL search_path TO tamara, pg_catalog")
                    raw.execute("SET LOCAL statement_timeout TO '30s'")
                    raw.execute("SET LOCAL lock_timeout TO '15s'")
                    yield PostgresConnection(raw)
            else:
                raw = sqlite3.connect(directory / "content.sqlite", timeout=15)
                raw.row_factory = sqlite3.Row
                try:
                    with raw:
                        yield raw
                finally:
                    raw.close()
        except BaseException:
            for callback in reversed(callbacks):
                try:
                    callback()
                except Exception:
                    app.logger.warning(
                        "No se pudo limpiar una imagen de una operación cancelada."
                    )
            raise
        finally:
            _rollback.reset(token)

    app.db = connection
    with connection() as c:
        if url:
            c.execute("BEGIN IMMEDIATE")
            c.execute("CREATE SCHEMA IF NOT EXISTS tamara")
            c.execute("REVOKE ALL ON SCHEMA tamara FROM PUBLIC")
            # Supabase browser roles must never reach the application's tables.
            for role in ("anon", "authenticated"):
                if c.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname=?", (role,)
                ).fetchone():
                    c.execute(f"REVOKE ALL ON SCHEMA tamara FROM {role}")
            schema = SCHEMA.replace("REAL", "DOUBLE PRECISION")
            for table in ("history", "panel_history"):
                schema = schema.replace(
                    f"{table}(id INTEGER PRIMARY KEY",
                    f"{table}(id BIGSERIAL PRIMARY KEY",
                )
            schema = schema.replace(
                "PRIMARY KEY(collection,id)",
                "sort_id BIGSERIAL,PRIMARY KEY(collection,id)",
            )
            for statement in schema.split(";"):
                if statement.strip():
                    c.execute(statement)
            for table in (
                "admins",
                "sessions",
                "attempts",
                "state",
                "history",
                "media",
                "panel_records",
                "panel_history",
            ):
                c.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
                c.execute(f"REVOKE ALL ON TABLE {table} FROM PUBLIC")
        else:
            c.executescript(SCHEMA)
        data = json.dumps(DEFAULT, ensure_ascii=False)
        c.execute(
            "INSERT INTO state VALUES(1,?,?,0) ON CONFLICT(id) DO NOTHING", (data, data)
        )
