"""Create the first administrator from temporary deployment secrets, once only."""

import os
from ..security import PH


def initialize_admin(app):
    if app.config["TESTING"]:
        return
    user = os.environ.get("TAMARA_ADMIN_USER", "").strip()
    password = os.environ.get("TAMARA_ADMIN_PASSWORD", "")
    if not user and not password:
        return
    with app.db() as c:
        c.execute("BEGIN IMMEDIATE")
        if c.execute("SELECT 1 FROM admins").fetchone():
            return  # Never reset an existing password on restart.
        if not user or len(user) > 100 or not 14 <= len(password) <= 1024:
            raise RuntimeError(
                "Para el primer administrador configura TAMARA_ADMIN_USER y TAMARA_ADMIN_PASSWORD (14 a 1024 caracteres)."
            )
        c.execute("INSERT INTO admins VALUES(?,?)", (user, PH.hash(password)))
