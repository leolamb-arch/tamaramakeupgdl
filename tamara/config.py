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
    environment = os.environ.get("APP_ENV", "development")
    if environment not in ("development", "production"):
        raise RuntimeError("APP_ENV debe ser development o production.")
    production = environment == "production"
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
    # An explicit data directory keeps local tools/tests isolated from cloud data.
    database_url = (
        "" if data_dir is not None else os.environ.get("DATABASE_URL", "").strip()
    )
    storage_url = (
        "" if data_dir is not None else os.environ.get("SUPABASE_URL", "").rstrip("/")
    )
    storage_key = (
        "" if data_dir is not None else os.environ.get("SUPABASE_SECRET_KEY", "")
    )
    bucket = (
        "" if data_dir is not None else os.environ.get("SUPABASE_STORAGE_BUCKET", "")
    )
    if database_url and urlsplit(database_url).scheme not in ("postgres", "postgresql"):
        raise RuntimeError("DATABASE_URL debe ser una conexión PostgreSQL.")
    if any((storage_url, storage_key, bucket)) and not all(
        (storage_url, storage_key, bucket)
    ):
        raise RuntimeError(
            "Completa SUPABASE_URL, SUPABASE_SECRET_KEY y SUPABASE_STORAGE_BUCKET."
        )
    if storage_url:
        endpoint = urlsplit(storage_url)
        if (
            endpoint.scheme != "https"
            or not endpoint.hostname
            or endpoint.path
            or endpoint.query
            or endpoint.fragment
            or endpoint.username
            or endpoint.password
        ):
            raise RuntimeError(
                "SUPABASE_URL debe ser un origen HTTPS sin ruta ni credenciales."
            )
        if not storage_key.startswith("sb_secret_"):
            raise RuntimeError(
                "SUPABASE_SECRET_KEY debe ser una Secret key (sb_secret_)."
            )
        if not bucket or any(
            c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in bucket
        ):
            raise RuntimeError("Nombre de bucket inválido.")
    if (
        production
        and data_dir is None
        and os.environ.get("RENDER") == "true"
        and not all((database_url, storage_url, storage_key, bucket))
    ):
        raise RuntimeError(
            "Render necesita PostgreSQL y Storage configurados; no se usarán datos temporales."
        )
    threads = int(os.environ.get("WAITRESS_THREADS", "8"))
    if not 1 <= threads <= 64:
        raise RuntimeError("WAITRESS_THREADS debe estar entre 1 y 64.")
    return dict(
        WAITRESS_THREADS=threads,
        TRUSTED_PROXY_CIDRS=os.environ.get("TRUSTED_PROXY_CIDRS", ""),
        DATABASE_URL=database_url,
        SUPABASE_URL=storage_url,
        SUPABASE_SECRET_KEY=storage_key,
        SUPABASE_STORAGE_BUCKET=bucket,
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
