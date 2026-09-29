"""Public pages and compatibility URLs for static resources."""

import json
from flask import Blueprint, abort, send_from_directory
from ..config import ROOT
from ..services.content import state
from ..services.rendering import render, render_public

bp = Blueprint("public", __name__)


@bp.get("/favicon.ico")
def favicon():
    return send_from_directory(
        ROOT / "static/assets", "logo-placeholder.svg", mimetype="image/svg+xml"
    )


@bp.get("/fonts.css")
def preview_fonts():
    # The panel's isolated preview copies the stylesheet into a document at /.
    return send_from_directory(
        ROOT / "static/vendor/reference-admin", "fonts.css", mimetype="text/css"
    )


@bp.get("/")
def home():
    return render_public(state()["published"])


@bp.get("/api/contact")
def contact():
    data = json.loads(state()["published"])
    return {
        "name": data["texts"]["t009"],
        "whatsapp": data["settings"]["whatsapp"] or data["settings"]["contactWhatsapp"],
    }


@bp.get("/preview")
def preview():
    return render(json.loads(state()["draft"]), True)


@bp.get("/<folder>/<path:name>")
def static_file(folder, name):
    if folder not in [
        "css",
        "js",
        "assets",
        "admin-assets",
        "shared",
        "reference-assets",
    ]:
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


@bp.get("/healthz")
def health():
    from ..database import db

    with db() as c:
        c.execute("SELECT 1").fetchone()
    return {"ok": True}


@bp.get("/robots.txt")
def robots():
    from flask import current_app, Response

    return Response(
        "User-agent: *\nDisallow: /admin\nDisallow: /login\nDisallow: /api/\nDisallow: /preview\nSitemap: "
        + current_app.config["ORIGIN"]
        + "/sitemap.xml\n",
        mimetype="text/plain",
    )


@bp.get("/sitemap.xml")
def sitemap():
    from flask import current_app, Response
    from xml.sax.saxutils import escape

    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'
        + escape(current_app.config["ORIGIN"] + "/")
        + "</loc></url></urlset>",
        mimetype="application/xml",
    )
