"""Paths and validated environment settings; never load secrets from public files."""

import os
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = json.loads((ROOT / "content/defaults.json").read_text(encoding="utf-8"))


def settings(data_dir=None):
    origin = os.environ.get("APP_ORIGIN", "http://127.0.0.1:8765").rstrip("/")
    parsed = urlsplit(origin)
    production = os.environ.get("APP_ENV") == "production"
    secret = os.environ.get("APP_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError(
            "Configura APP_SECRET con al menos 32 caracteres aleatorios en el entorno."
        )
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise RuntimeError(
            "APP_ORIGIN debe ser un origen HTTP(S), sin ruta ni credenciales."
        )
    if production and parsed.scheme != "https":
        raise RuntimeError("APP_ORIGIN debe usar HTTPS en producción.")
    ttl = int(os.environ.get("SESSION_SECONDS", "28800"))
    idle = int(os.environ.get("SESSION_IDLE_SECONDS", "1800"))
    if ttl <= 0 or idle <= 0:
        raise RuntimeError("Los tiempos de sesión deben ser positivos.")
    return dict(
        SECRET_KEY=secret,
        ORIGIN=origin,
        PRODUCTION=production,
        DATA_DIR=Path(
            data_dir or os.environ.get("DATA_DIR", ROOT / "private")
        ).resolve(),
        SESSION_SECONDS=ttl,
        SESSION_IDLE_SECONDS=idle,
        MAX_CONTENT_LENGTH=9 * 1024 * 1024,
        MAX_FORM_PARTS=200,
        TRUSTED_HOSTS=[parsed.hostname],
    )
