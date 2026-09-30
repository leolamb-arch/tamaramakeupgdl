"""Authenticated editor endpoints; access is enforced by the global guard."""

import json
from flask import Blueprint, jsonify, send_from_directory
from ..config import ROOT, DEFAULT
from ..database import db
from ..services.content import state, update

bp = Blueprint("admin", __name__)


@bp.get("/admin")
def admin_page():
    return (ROOT / "templates/admin/index.html").read_text(encoding="utf-8")


@bp.get("/api/admin/content")
def content():
    row = state()
    return jsonify(
        content=json.loads(row["draft"]),
        revision=row["revision"],
        defaults=DEFAULT,
        labels=json.loads((ROOT / "content/labels.json").read_text(encoding="utf-8")),
    )


@bp.post("/api/admin/draft")
def draft():
    return update("draft")


@bp.post("/api/admin/publish")
def publish():
    return update("publish")


@bp.post("/api/admin/restore/<int:version>")
def restore(version):
    return update("restore", version=version)


@bp.get("/api/admin/history")
def history():
    with db() as c:
        rows = c.execute(
            "SELECT id,created,user,action FROM history ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@bp.get("/reference-assets/<path:filename>")
def reference_assets(filename):
    return send_from_directory(
        ROOT / "static/vendor/reference-admin",
        filename,
    )

@bp.get("/api/admin/media")
def media_list():
    with db() as c:
        rows = c.execute("SELECT * FROM media ORDER BY created DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@bp.post("/api/admin/full-content")
def full_content():
    return update("full")


@bp.post("/api/admin/restore-publish/<int:version>")
def restore_publish(version):
    return update("restore-publish", version=version)
