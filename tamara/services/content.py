"""Draft/publication boundaries and version history."""

import json
import time
from flask import g, abort, jsonify
from ..database import db
from ..config import DEFAULT
from ..validation import json_body, validate


def state():
    with db() as c:
        return c.execute("SELECT * FROM state WHERE id=1").fetchone()


def public_content(data):
    data = json.loads(json.dumps(data))
    data["services"] = [s for s in data["services"] if s["status"] == "visible"]
    used = set(DEFAULT["images"]) - set(
        v for s in DEFAULT["services"] for v in s["images"]
    )
    used.update(v for s in data["services"] for v in s["images"])
    data["images"] = {k: v for k, v in data["images"].items() if k in used}
    return data


def update(action, content=None, version=None):
    body = json_body()
    if content is None and action == "draft":
        try:
            content = validate(body.get("content"))
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            abort(
                400,
                description=(
                    str(e)
                    if isinstance(e, ValueError)
                    else "Revisa los campos del contenido."
                ),
            )
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT * FROM state WHERE id=1").fetchone()
        if body.get("revision") != row["revision"]:
            abort(
                409,
                description="El contenido cambió en otra pestaña. Recarga antes de editar.",
            )
        if action == "publish":
            content = json.loads(row["draft"])
        if action == "restore":
            old = c.execute(
                "SELECT content FROM history WHERE id=?", (version,)
            ).fetchone()
            if not old:
                abort(404)
            content = json.loads(old["content"])
        packed = json.dumps(content, ensure_ascii=False)
        # Record the previous draft as well, so the first save can be undone.
        if not c.execute("SELECT 1 FROM history LIMIT 1").fetchone():
            c.execute(
                "INSERT INTO history(created,user,action,content) VALUES(?,?,?,?)",
                (time.time(), g.session["user"], "original", row["draft"]),
            )
        c.execute(
            "UPDATE state SET draft=?,published=?,revision=revision+1 WHERE id=1",
            (packed, packed if action == "publish" else row["published"]),
        )
        c.execute(
            "INSERT INTO history(created,user,action,content) VALUES(?,?,?,?)",
            (time.time(), g.session["user"], action, packed),
        )
    return jsonify(ok=True, revision=row["revision"] + 1)
