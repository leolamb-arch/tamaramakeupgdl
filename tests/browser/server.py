"""Isolated browser fixture, never uses deployment data or a real administrator."""

import os
import tempfile
from tamara import create_app
from tamara.security import PH
from waitress import serve

with tempfile.TemporaryDirectory(prefix="tamara-browser-") as directory:
    app = create_app(data_dir=directory, testing=True)
    with app.db() as connection:
        connection.execute(
            "INSERT INTO admins VALUES(?,?)",
            ("test-admin", PH.hash(os.environ["TEST_ADMIN_PASSWORD"])),
        )
    print("READY", flush=True)
    serve(
        app, host="127.0.0.1", port=int(os.environ.get("TEST_PORT", "8877")), threads=8
    )
