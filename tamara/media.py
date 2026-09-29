"""Private uploads become public only when referenced by published content."""

import json
import re
import secrets
import time
from flask import (
    Blueprint,
    current_app,
    request,
    g,
    abort,
    jsonify,
    send_from_directory,
)
from ..database import db
from ..services.content import state, public_content
from ..services.images import decode_image
from ..services.reference_panel import public_settings

bp = Blueprint("media", __name__)


@bp.post("/api/admin/upload")
def upload():
    directory = current_app.config["DATA_DIR"]
    f = request.files.get("file")
    if not f:
        abort(400, description="Selecciona una imagen.")
    raw = f.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        abort(413, description="Máximo 8 MB por imagen.")
    clean = decode_image(raw)
    name = secrets.token_hex(16) + ".webp"
    thumb = name.replace(".webp", "-thumb.webp")
    try:
        clean.save(directory / "uploads" / name, "WEBP", quality=85)
        w, h = clean.size
        clean.thumbnail((480, 480))
        clean.save(directory / "uploads" / thumb, "WEBP", quality=80)
        with db() as c:
            c.execute(
                "INSERT INTO media VALUES(?,?,?,?,?)",
                (name, time.time(), g.session["user"], w, h),
            )
    except Exception:
        # No database row should point to a partial upload; remove partial files on failure.
        for filename in (name, thumb):
            (directory / "uploads" / filename).unlink(missing_ok=True)
        raise
    return jsonify(src="/media/" + name, width=w, height=h)


@bp.get("/media/<name>")
def media(name):
    directory = current_app.config["DATA_DIR"]
    if not re.fullmatch(r"[a-f0-9]{32}(-thumb)?\.webp", name):
        abort(404)
    base = name.replace("-thumb", "")
    if not g.session or not g.session["user"]:
        published = public_content(json.loads(state()["published"]))
        allowed={v["src"] for v in published["images"].values()}
        allowed.update(item.get('photo','') for item in public_settings().get('testimonials',[]))
        if "/media/" + base not in allowed:
            abort(404)
    return send_from_directory(directory / "uploads", name)
