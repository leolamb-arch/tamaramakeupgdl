import copy
import io
import json
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
from PIL import Image
from tamara import create_app
from tamara.security import PH
from tamara.services import reference_panel as panel
from tamara.services.backups import backup, restore


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = secrets.token_urlsafe(24)
        cls.password_hash = PH.hash(cls.password)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(
            os.environ,
            {
                "APP_SECRET": secrets.token_urlsafe(48),
                "APP_ORIGIN": "http://localhost",
                "APP_ENV": "development",
                "TRUSTED_PROXY_CIDRS": "",
            },
        )
        self.environment.start()
        self.app = create_app(data_dir=self.directory.name, testing=True)
        self.client = self.app.test_client()
        with self.app.db() as c:
            c.execute(
                "INSERT INTO admins VALUES(?,?)", ("test-admin", self.password_hash)
            )
        self.headers = self.session(self.client)

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def session(self, client):
        client.get("/login")
        return {
            "Origin": "http://localhost",
            "X-CSRF-Token": client.get("/api/session").json["csrf"],
        }

    def login(self):
        result = self.client.post(
            "/api/login",
            json={"name": "test-admin", "password": self.password},
            headers=self.headers,
        )
        self.assertEqual(result.status_code, 200)
        self.headers = self.session(self.client)

    def post(self, path, value, headers=None):
        return self.client.post(path, json=value, headers=headers or self.headers)

    def records(self, name):
        return self.client.get("/api/admin/reference/" + name).json

    def save(self, collection, record, values):
        return self.post(
            "/api/admin/reference/" + collection + "/" + record["id"],
            values,
            {**self.headers, "X-Record-Version": str(record["_version"])},
        )

    def payload(self):
        with self.app.app_context(), self.app.db() as c:
            for offset in range(1, 9):
                day = (
                    (
                        datetime.now(ZoneInfo("America/Mexico_City"))
                        + timedelta(days=offset)
                    )
                    .date()
                    .isoformat()
                )
                times = panel.slots(c, day)
                if times:
                    break
        return dict(
            nombre="Cliente prueba",
            telefono="3312345678",
            email="cliente@example.com",
            servicio="social",
            personas=2,
            ubicacion="Otra ubicación",
            direccion="Dirección de prueba",
            comentarios="Prueba",
            fecha=day,
            hora=times[0],
            request_id=secrets.token_hex(16),
        )

    def test_private_routes_and_csrf(self):
        for path in ["/api/admin/content", "/api/admin/reference/bookings", "/preview"]:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.login()
        self.assertEqual(
            self.post(
                "/api/admin/logout", {}, {"Origin": "http://localhost"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.post(
                "/api/admin/logout",
                {},
                {**self.headers, "Origin": "https://evil.example"},
            ).status_code,
            403,
        )
        self.assertEqual(self.post("/api/admin/logout", {}).status_code, 200)
        self.assertEqual(self.client.get("/api/admin/content").status_code, 401)

    def test_login_limit(self):
        for _ in range(5):
            self.assertEqual(
                self.post(
                    "/api/login", {"name": "test-admin", "password": "incorrect"}
                ).status_code,
                401,
            )
        self.assertEqual(
            self.post(
                "/api/login", {"name": "test-admin", "password": self.password}
            ).status_code,
            429,
        )

    def test_site_types_rejected_without_publication(self):
        self.login()
        record = self.records("site_content")[0]
        for field, value in [("tagline", 123), ("name", []), ("testimonials", None)]:
            body = copy.deepcopy(record["data"])
            body[field] = value
            self.assertEqual(
                self.save("site_content", record, {"data": body}).status_code, 400
            )
            self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(
            self.records("site_content")[0]["_version"], record["_version"]
        )

    def test_valid_site_and_appearance(self):
        self.login()
        for collection in ("site_content", "appearance"):
            record = self.records(collection)[0]
            result = self.save(collection, record, {"data": record["data"]})
            self.assertEqual(result.status_code, 200, result.json)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_service_validation_and_conflicts(self):
        self.login()
        record = self.records("services")[0]
        for value in [0.5, True, -1, 1000]:
            self.assertEqual(
                self.save("services", record, {"cover_index": value}).status_code, 400
            )
        self.assertEqual(
            self.save("services", record, {"name": "Nombre nuevo"}).status_code, 200
        )
        self.assertEqual(
            self.save("services", record, {"name": "Edición obsoleta"}).status_code, 409
        )

    def test_restore_survives_unrelated_edit(self):
        self.login()
        first = self.records("services")[0]
        original = first["name"]
        self.assertEqual(
            self.save("services", first, {"name": "Nuevo"}).status_code, 200
        )
        versions = self.client.get("/api/admin/history").json
        version = next(v["id"] for v in versions if v["action"] == "antes-panel")
        revision = self.client.get("/api/admin/content").json["revision"]
        self.assertEqual(
            self.post(
                f"/api/admin/restore-publish/{version}", {"revision": revision}
            ).status_code,
            200,
        )
        self.assertEqual(self.records("services")[0]["name"], original)
        other = self.records("services")[1]
        self.assertEqual(
            self.save("services", other, {"description": "Otro texto"}).status_code, 200
        )
        with self.app.db() as c:
            content = json.loads(c.execute("SELECT published FROM state").fetchone()[0])
        self.assertEqual(content["services"][0]["name"], original)
        public = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('"_panel"', public)
        self.assertNotIn("request_hash", public)

    def test_full_editor_and_old_draft_publish(self):
        self.login()
        value = self.client.get("/api/admin/content").json
        value["content"]["texts"]["t001"] = "Navegación de prueba"
        response = self.post(
            "/api/admin/draft",
            {"content": value["content"], "revision": value["revision"]},
        )
        self.assertEqual(response.status_code, 200, response.json)
        self.assertNotIn(
            "Navegación de prueba", self.client.get("/").get_data(as_text=True)
        )
        self.assertIn(
            "Navegación de prueba", self.client.get("/preview").get_data(as_text=True)
        )
        self.assertEqual(
            self.post(
                "/api/admin/publish", {"revision": response.json["revision"]}
            ).status_code,
            200,
        )
        self.assertIn(
            "Navegación de prueba", self.client.get("/").get_data(as_text=True)
        )

    def test_booking_pending_idempotent_and_private(self):
        payload = self.payload()
        response = self.post("/api/booking/requests", payload)
        self.assertEqual(response.status_code, 201, response.json)
        self.assertEqual(response.json["status"], "pending")
        identity = response.json["id"]
        self.assertEqual(
            self.post("/api/booking/requests", payload).json["id"], identity
        )
        changed = {**payload, "nombre": "Otro cliente"}
        self.assertEqual(self.post("/api/booking/requests", changed).status_code, 409)
        with self.app.app_context(), self.app.db() as c:
            self.assertIn(payload["hora"], panel.slots(c, payload["fecha"]))
        self.assertNotIn(
            payload["telefono"], self.client.get("/").get_data(as_text=True)
        )
        self.login()
        rows = self.records("bookings")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["client_name"], payload["nombre"])
        self.assertEqual(rows[0]["deposit"], 0)

    def test_booking_rejects_invalid_and_injected_fields(self):
        original = self.payload()
        for key, value in [
            ("nombre", "<script>"),
            ("personas", 0),
            ("personas", 1.5),
            ("fecha", "2000-01-01"),
            ("servicio", "unknown"),
            ("hora", "25:00"),
            ("email", "bad"),
        ]:
            self.assertEqual(
                self.post(
                    "/api/booking/requests", {**original, key: value}
                ).status_code,
                400,
            )
        self.assertEqual(
            self.post("/api/booking/requests", {**original, "total": 1}).status_code,
            400,
        )

    def test_booking_rate_limit(self):
        payload = self.payload()
        for _ in range(5):
            payload["request_id"] = secrets.token_hex(16)
            self.assertEqual(
                self.post("/api/booking/requests", payload).status_code, 201
            )
        payload["request_id"] = secrets.token_hex(16)
        self.assertEqual(self.post("/api/booking/requests", payload).status_code, 429)

    def test_hidden_service_cannot_be_requested(self):
        payload = self.payload()
        self.login()
        service = next(
            row
            for row in self.records("services")
            if row["slug"] == payload["servicio"]
        )
        self.assertEqual(
            self.save("services", service, {"active": False}).status_code, 200
        )
        self.assertEqual(self.post("/api/booking/requests", payload).status_code, 400)

    def test_image_private_until_published_and_sanitized(self):
        self.login()
        image = io.BytesIO()
        Image.new("RGB", (64, 64), "red").save(image, "PNG")
        image.seek(0)
        response = self.client.post(
            "/api/admin/upload",
            data={"file": (image, "test.png")},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        src = response.json["src"]
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get(src).status_code, 404)
        value = self.client.get("/api/admin/content").json
        value["content"]["images"]["assets/portada-retrato.svg"]["src"] = src
        result = self.post(
            "/api/admin/full-content",
            {"revision": value["revision"], "content": value["content"]},
        )
        self.assertEqual(result.status_code, 200, result.json)
        with anonymous.get(src) as result:
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.mimetype, "image/webp")

    def test_reject_svg_upload_and_traversal(self):
        self.login()
        response = self.client.post(
            "/api/admin/upload",
            data={"file": (io.BytesIO(b"<svg/>"), "evil.svg")},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.client.get("/assets/../../tamara/config.py").status_code, 404
        )

    def test_backup_restore_and_sessions(self):
        self.login()
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "copy"
            backup(self.app, target)
            first = self.records("services")[0]
            self.save("services", first, {"name": "After backup"})
            restore(self.app, target)
        self.assertEqual(self.client.get("/api/admin/content").status_code, 401)
        with self.app.app_context(), self.app.db() as c:
            self.assertEqual(panel.records(c, "services")[0]["name"], first["name"])

    def test_first_full_edit_restores_original_panel(self):
        self.login()
        before = self.records("site_content")[0]["data"]["tagline"]
        value = self.client.get("/api/admin/content").json
        value["content"]["texts"]["t011"] = "Primera edición"
        result = self.post(
            "/api/admin/full-content",
            {"revision": value["revision"], "content": value["content"]},
        )
        self.assertEqual(result.status_code, 200)
        original = next(
            row["id"]
            for row in self.client.get("/api/admin/history").json
            if row["action"] == "original"
        )
        self.assertEqual(
            self.post(
                f"/api/admin/restore-publish/{original}",
                {"revision": result.json["revision"]},
            ).status_code,
            200,
        )
        self.assertEqual(self.records("site_content")[0]["data"]["tagline"], before)

    def test_complete_editor_preserves_advanced_testimonials(self):
        self.login()
        site = self.records("site_content")[0]
        data = site["data"]
        data["testimonials"][0]["name"] = "Testimonio avanzado"
        self.assertEqual(
            self.save("site_content", site, {"data": data}).status_code, 200
        )
        value = self.client.get("/api/admin/content").json
        value["content"]["texts"]["t001"] = "Menú cambiado"
        self.assertEqual(
            self.post(
                "/api/admin/full-content",
                {"revision": value["revision"], "content": value["content"]},
            ).status_code,
            200,
        )
        self.assertEqual(
            self.records("site_content")[0]["data"]["testimonials"][0]["name"],
            "Testimonio avanzado",
        )

    def test_booking_export_flags_and_delete(self):
        response = self.post("/api/booking/requests", self.payload())
        self.assertEqual(response.status_code, 201)
        self.login()
        record = self.records("bookings")[0]
        result = self.save("bookings", record, {"exported_apple": True})
        self.assertEqual(result.status_code, 200, result.json)
        self.assertTrue(self.records("bookings")[0]["exported_apple"])
        self.assertEqual(
            self.save("bookings", result.json, {"status": "confirmed"}).status_code, 400
        )
        self.assertEqual(
            self.post(
                "/api/admin/reference-tools/schedule/delete-booking",
                {"bookingId": record["id"], "mode": "free"},
            ).status_code,
            200,
        )
        self.assertEqual(self.records("bookings"), [])

    def test_metadata_and_headers(self):
        response = self.client.get("/")
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn('rel="canonical"', response.get_data(as_text=True))
        self.assertEqual(self.client.get("/robots.txt").status_code, 200)
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
        self.assertEqual(self.client.get("/healthz").status_code, 200)

    def test_schedule_validation(self):
        self.login()
        schedule = self.records("schedule_config")[0]
        self.assertEqual(
            self.save(
                "schedule_config", schedule, {"appointment_duration": 0}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.save(
                "schedule_config",
                schedule,
                {"time_blocks": [{"start": "15:00", "end": "14:00"}]},
            ).status_code,
            400,
        )

    def test_proxy_headers_only_from_allowed_networks(self):
        from tamara.proxy import TrustedProxy

        def endpoint(environ, start_response):
            start_response("200 OK", [])
            return [environ["REMOTE_ADDR"].encode()]

        app = TrustedProxy(endpoint, "10.0.0.0/8")
        for address, expected in [
            ("192.0.2.1", "192.0.2.1"),
            ("10.0.0.1", "198.51.100.3"),
        ]:
            result = app(
                {"REMOTE_ADDR": address, "HTTP_X_FORWARDED_FOR": "198.51.100.3"},
                lambda *args: None,
            )
            self.assertEqual(result[0].decode(), expected)


if __name__ == "__main__":
    unittest.main()
