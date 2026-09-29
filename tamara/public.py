"""Public pages and compatibility URLs for static resources."""

import json
from flask import Blueprint, abort, send_from_directory
from ..config import ROOT
from ..services.content import state
from ..services.rendering import render, render_public

bp = Blueprint("public", __name__)


@bp.get("/")
def home():
    return render_public(state()["published"])


@bp.get("/preview")
def preview():
    return render(json.loads(state()["draft"]), True)


@bp.get("/<folder>/<path:name>")
def static_file(folder, name):
    if folder not in ["css", "js", "assets", "admin-assets", "shared", "reference-assets"]:
        abort(404)
    if folder == "js" and name == "services.js":
        abort(404)
    mapping = {
        "css": "static/css",
        "js": "static/js/public",
        "shared": "static/js/shared",
        "assets": "static/assets",
        "admin-assets": "static/js/admin",
        "reference-assets": "static/vendor/reference-admin",
    }
    if folder == "admin-assets" and name == "admin.css":
        return send_from_directory(ROOT / "static/css", name)
    return send_from_directory(ROOT / mapping[folder], name)
