"""SQLite connections are scoped to each operation, including CLI operations."""

import sqlite3
import json
from contextlib import contextmanager
from flask import current_app
from .config import DEFAULT


def db():
    return current_app.db()


def configure_database(app):
    directory = app.config["DATA_DIR"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "uploads").mkdir(exist_ok=True)

    @contextmanager
    def db():
        c = sqlite3.connect(directory / "content.sqlite", timeout=15)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    app.db = db
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS admins(name TEXT PRIMARY KEY, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user TEXT, csrf TEXT NOT NULL, expires REAL NOT NULL, seen REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(scope TEXT, created REAL);
        CREATE INDEX IF NOT EXISTS attempts_scope ON attempts(scope,created);
        CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1), draft TEXT NOT NULL, published TEXT NOT NULL, revision INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, created REAL NOT NULL, user TEXT NOT NULL, action TEXT NOT NULL, content TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY, created REAL NOT NULL, user TEXT NOT NULL, width INTEGER, height INTEGER);
        """)
        data = json.dumps(DEFAULT, ensure_ascii=False)
        c.execute("INSERT OR IGNORE INTO state VALUES(1,?,?,0)", (data, data))
