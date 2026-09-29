"""Private uploads become public only when referenced by published content."""

import json
import re
import secrets
import time
from flask import (
    Blueprint,
    request,
    g,
    abort,
    jsonify,
)
from ..database import db
from ..services.content import state, public_content
from ..services.images import decode_image
from ..services import storage
from ..services.reference_panel import public_settings

bp = Blueprint("media", __name__)


@bp.post("/api/admin/upload")
def upload():
    f = request.files.get("file")
    if not f:
        abort(400, description="Selecciona una imagen.")
    raw = f.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        abort(413, description="Máximo 8 MB por imagen.")
    clean = decode_image(raw)
    name = secrets.token_hex(16) + ".webp"
    with db() as c:
        w, h = storage.save_pair(clean, name)
        c.execute(
            "INSERT INTO media VALUES(?,?,?,?,?)",
            (name, time.time(), g.session["user"], w, h),
        )
    return jsonify(src="/media/" + name, width=w, height=h)


@bp.get("/media/<name>")
def media(name):
    if not re.fullmatch(r"[a-f0-9]{32}(-thumb)?\.webp", name):
        abort(404)
    base = name.replace("-thumb", "")
    if not g.session or not g.session["user"]:
        published = public_content(json.loads(state()["published"]))
        allowed = {v["src"] for v in published["images"].values()}
        allowed.update(
            item.get("photo", "") for item in public_settings().get("testimonials", [])
        )
        if "/media/" + base not in allowed:
            abort(404)
    return storage.serve(name)
