"""Offline backup/restore. Stage and validate before touching the active database."""

import json
import re
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


def backup(app, target):
    target.mkdir(parents=True, exist_ok=False)
    try:
        with (
            app.db() as source,
            closing(sqlite3.connect(target / "content.sqlite")) as dest,
        ):
            source.backup(dest)
            with dest:
                dest.execute("DELETE FROM sessions")
                dest.execute("DELETE FROM attempts")
        shutil.copytree(app.config["DATA_DIR"] / "uploads", target / "uploads")
    except Exception:
        # Keep a partial backup clearly marked so it cannot be restored accidentally.
        (target / "INCOMPLETE").write_text(
            "La copia no terminó correctamente.", encoding="utf-8"
        )
        raise


def validate_backup(folder):
    if (folder / "INCOMPLETE").exists():
        raise ValueError("La copia está marcada como incompleta.")
    with closing(
        sqlite3.connect(
            f'file:{(folder / "content.sqlite").as_posix()}?mode=ro', uri=True
        )
    ) as source:
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Base dañada.")
        required = {"admins", "sessions", "attempts", "state", "history", "media"}
        actual = {
            r[0]
            for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not required.issubset(actual):
            raise ValueError("La copia no contiene el esquema de Tamara.")
        row = source.execute(
            "SELECT draft,published,revision FROM state WHERE id=1"
        ).fetchone()
        if row is None:
            raise ValueError("Falta el contenido de la copia.")
        for packed in row[:2]:
            data = json.loads(packed)
            if not isinstance(data, dict) or not {
                "texts",
                "seo",
                "theme",
                "settings",
                "images",
                "services",
            }.issubset(data):
                raise ValueError("Contenido inválido en la copia.")
        # Check all registered images, including those retained only for history.
        for (name,) in source.execute("SELECT id FROM media"):
            if not re.fullmatch(r"[a-f0-9]{32}\.webp", name):
                raise ValueError("Nombre de imagen inválido en la copia.")
            for item in (name, name.replace(".webp", "-thumb.webp")):
                file = folder / "uploads" / item
                if not file.is_file() or file.is_symlink():
                    raise ValueError(
                        "La copia contiene imágenes faltantes o enlaces simbólicos."
                    )


def restore(app, target):
    """Recover normal I/O failures; the server must remain stopped during this operation."""
    data = app.config["DATA_DIR"]
    validate_backup(target)
    with tempfile.TemporaryDirectory(prefix="tamara-restore-", dir=data) as temp:
        stage = Path(temp)
        shutil.copytree(target / "uploads", stage / "incoming")
        shutil.copy2(target / "content.sqlite", stage / "incoming.sqlite")
        # Save a rollback snapshot before replacing any files.
        with (
            app.db() as src,
            closing(sqlite3.connect(stage / "previous.sqlite")) as prev,
        ):
            src.backup(prev)
        installed = []
        database_started = False
        try:
            for incoming in (stage / "incoming").iterdir():
                if not incoming.is_file() or incoming.is_symlink():
                    raise ValueError(
                        "La carpeta de imágenes contiene un archivo no permitido."
                    )
                dest = data / "uploads" / incoming.name
                previous = stage / "previous" / incoming.name
                previous.parent.mkdir(exist_ok=True)
                if dest.exists():
                    shutil.copy2(dest, previous)
                incoming.replace(dest)
                installed.append((dest, previous))
            # Publish the database only after every image is installed.
            database_started = True
            with (
                closing(sqlite3.connect(stage / "incoming.sqlite")) as src,
                app.db() as dest,
            ):
                src.backup(dest)
                dest.execute("DELETE FROM sessions")
                dest.execute("DELETE FROM attempts")
        except Exception:
            for dest, previous in reversed(installed):
                if previous.exists():
                    previous.replace(dest)
                else:
                    dest.unlink(missing_ok=True)
            if database_started:
                with (
                    closing(sqlite3.connect(stage / "previous.sqlite")) as prev,
                    app.db() as dest,
                ):
                    prev.backup(dest)
            raise
