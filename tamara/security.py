"""Authentication primitives and request protections shared by all routes."""

import secrets
import time
import hashlib
import hmac
from flask import current_app, request, g, abort, redirect, jsonify
from argon2 import PasswordHasher
from .database import db

PH = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY = PH.hash(secrets.token_urlsafe(32))


def digest(value):
    return hmac.new(
        current_app.config["SECRET_KEY"].encode(), value.encode(), hashlib.sha256
    ).hexdigest()


def session_response(response, user=None):
    ttl = current_app.config["SESSION_SECONDS"]
    idle = current_app.config["SESSION_IDLE_SECONDS"]
    production = current_app.config["PRODUCTION"]
    origin = current_app.config["ORIGIN"]
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    now = time.time()
    with db() as c:
        c.execute("DELETE FROM sessions WHERE expires<? OR seen<?", (now, now - idle))
        old = request.cookies.get("tamara_session", "")
        if old:
            c.execute("DELETE FROM sessions WHERE token=?", (digest(old),))
        c.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?)",
            (digest(token), user, csrf, now + (ttl if user else 600), now),
        )
    response.set_cookie(
        "tamara_session",
        token,
        httponly=True,
        secure=production,
        samesite="Strict",
        max_age=ttl if user else 600,
        path="/",
    )
    return response


def require_admin():
    if not g.session or not g.session["user"]:
        abort(401, description="Inicia sesión para continuar.")


def guard():
    ttl = current_app.config["SESSION_SECONDS"]
    idle = current_app.config["SESSION_IDLE_SECONDS"]
    production = current_app.config["PRODUCTION"]
    origin = current_app.config["ORIGIN"]
    g.session = None
    token = request.cookies.get("tamara_session", "")
    if token:
        with db() as c:
            g.session = c.execute(
                "SELECT * FROM sessions WHERE token=? AND expires>? AND seen>?",
                (digest(token), time.time(), time.time() - idle),
            ).fetchone()
            if g.session and time.time() - g.session["seen"] >= 30:
                c.execute(
                    "UPDATE sessions SET seen=? WHERE token=?",
                    (time.time(), digest(token)),
                )
    if request.path.startswith("/api/admin") or request.path in [
        "/admin",
        "/preview",
    ]:
        if request.path == "/admin" and (not g.session or not g.session["user"]):
            return redirect("/login")
        require_admin()
    if request.method not in ["GET", "HEAD", "OPTIONS"]:
        if request.headers.get("Origin") != origin:
            abort(403, description="Origen no autorizado.")
        if not g.session or not hmac.compare_digest(
            request.headers.get("X-CSRF-Token", ""), g.session["csrf"]
        ):
            abort(
                403,
                description="Sesión o token de seguridad vencido. Recarga la página.",
            )


def security(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; font-src 'self'; connect-src 'self'; frame-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'; object-src 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Private pages and uploads must never be reused across session/publication changes.
    if request.endpoint == "public.static_file":
        response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
    else:
        response.headers["Cache-Control"] = "no-store"
    if current_app.config["PRODUCTION"]:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


def http_error(e):
    return jsonify(error=e.description), e.code
