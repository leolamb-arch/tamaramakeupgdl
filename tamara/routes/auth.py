"""Login, session inspection and revocation."""

import time
from flask import Blueprint, current_app, request, g, abort, jsonify, make_response
from argon2.exceptions import VerificationError
from ..config import ROOT
from ..database import db
from ..validation import json_body
from ..security import PH, DUMMY, digest, session_response

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login_page():
    r = make_response((ROOT / "templates/admin/login.html").read_text(encoding="utf-8"))
    return r if g.session else session_response(r)


@bp.get("/api/session")
def session_info():
    if not g.session:
        abort(401, description="Recarga la página para iniciar sesión.")
    return jsonify(
        csrf=g.session["csrf"],
        authenticated=bool(g.session["user"]),
        user=g.session["user"],
    )


@bp.post("/api/login")
def login():
    body = json_body()
    name = body.get("name", "")
    password = body.get("password", "")
    if (
        not isinstance(name, str)
        or not isinstance(password, str)
        or len(name) > 100
        or len(password) > 1024
    ):
        abort(400)
    now = time.time()
    scope = digest("ip:" + str(request.remote_addr))
    account = digest("account:" + name.casefold())
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        c.execute("DELETE FROM attempts WHERE created<?", (now - 900,))
        if any(
            c.execute("SELECT COUNT(*) FROM attempts WHERE scope=?", (s,)).fetchone()[0]
            >= limit
            for s, limit in [(scope, 20), (account, 5)]
        ):
            abort(429, description="Demasiados intentos. Espera 15 minutos.")
        c.executemany(
            "INSERT INTO attempts VALUES(?,?)", [(scope, now), (account, now)]
        )
        row = c.execute("SELECT password FROM admins WHERE name=?", (name,)).fetchone()
    try:
        PH.verify(row["password"] if row else DUMMY, password)
        valid = bool(row)
    except VerificationError:
        valid = False
    if not valid:
        abort(401, description="Usuario o contraseña incorrectos.")
    with db() as c:
        c.execute("DELETE FROM attempts WHERE scope=?", (account,))
        c.execute("DELETE FROM attempts WHERE scope=? AND created=?", (scope, now))
    return session_response(jsonify(ok=True), name)


@bp.post("/api/admin/logout")
def logout():
    with db() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (g.session["token"],))
    r = jsonify(ok=True)
    r.delete_cookie(
        "tamara_session",
        path="/",
        secure=current_app.config["PRODUCTION"],
        httponly=True,
        samesite="Strict",
    )
    return r


@bp.post("/api/admin/revoke")
def revoke():
    with db() as c:
        c.execute("DELETE FROM sessions WHERE user=?", (g.session["user"],))
    r = jsonify(ok=True)
    r.delete_cookie("tamara_session", path="/")
    return r
