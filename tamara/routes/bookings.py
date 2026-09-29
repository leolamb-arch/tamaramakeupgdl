"""Public requests are pending leads, never automatic reservations or payments."""

import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, g, jsonify, request
from ..database import db
from ..security import digest, session_response
from ..validation import json_body, text
from ..services import reference_panel as panel

bp = Blueprint("bookings", __name__)


@bp.get("/api/booking/session")
def session():
    if not g.session:
        return session_response(jsonify(ready=True))
    return jsonify(ready=True)


@bp.post("/api/booking/requests")
def create():
    body = json_body()
    try:
        expected = {
            "nombre",
            "telefono",
            "email",
            "servicio",
            "personas",
            "ubicacion",
            "direccion",
            "comentarios",
            "fecha",
            "hora",
            "request_id",
        }
        if set(body) != expected:
            raise ValueError("Revisa los campos de la solicitud.")
        name = text(body["nombre"], 120).strip()
        phone = text(body["telefono"], 30).strip()
        email = text(body["email"], 254).strip()
        if (
            not name
            or not re.fullmatch(r"[+0-9 ()\-]{8,20}", phone)
            or len(re.sub(r"\D", "", phone)) < 8
        ):
            raise ValueError("Escribe tu nombre y un teléfono válido.")
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Revisa el correo electrónico.")
        people = body["personas"]
        if type(people) is not int or not 1 <= people <= 100:
            raise ValueError("Selecciona entre 1 y 100 personas.")
        if body["ubicacion"] not in ("Estudio de Tamara", "Otra ubicación"):
            raise ValueError("Selecciona la ubicación.")
        location = text(body["direccion"], 1000).strip()
        if body["ubicacion"] == "Otra ubicación" and not location:
            raise ValueError("Escribe y confirma la dirección.")
        notes = text(body["comentarios"], 3000)
        key = text(body["request_id"], 64)
        if not re.fullmatch(r"[a-zA-Z0-9-]{16,64}", key):
            raise ValueError("Identificador inválido. Recarga el formulario.")
        day, hour = text(body["fecha"], 10), text(body["hora"], 5)
        panel.minutes(hour)
        when = datetime.strptime(day + " " + hour, "%Y-%m-%d %H:%M").replace(
            tzinfo=ZoneInfo("America/Mexico_City")
        )
        now = datetime.now(ZoneInfo("America/Mexico_City"))
        if when <= now or when > now + timedelta(days=730):
            raise ValueError("Elige una fecha futura dentro de los próximos dos años.")
        identity = digest("booking:" + g.session["token"] + ":" + key)[:32]
        fingerprint = hashlib.sha256(
            json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        with db() as c:
            c.execute("BEGIN IMMEDIATE")
            existing = c.execute(
                "SELECT data FROM panel_records WHERE collection=? AND id=?",
                ("bookings", identity),
            ).fetchone()
            if existing:
                if json.loads(existing["data"]).get("request_hash") != fingerprint:
                    abort(
                        409,
                        description="La solicitud ya se envió con otros datos. Recarga para iniciar otra.",
                    )
                return jsonify(id=identity, status="pending", duplicate=True)
            scope = digest("booking-ip:" + str(request.remote_addr))
            stamp = time.time()
            c.execute("DELETE FROM attempts WHERE created<?", (stamp - 900,))
            if (
                c.execute(
                    "SELECT COUNT(*) FROM attempts WHERE scope=?", (scope,)
                ).fetchone()[0]
                >= 5
            ):
                abort(
                    429,
                    description="Has enviado varias solicitudes. Espera 15 minutos o contáctanos por WhatsApp.",
                )
            published = json.loads(
                c.execute("SELECT published FROM state WHERE id=1").fetchone()[0]
            )
            service = next(
                (
                    s
                    for s in published["services"]
                    if s["slug"] == body["servicio"] and s["status"] == "visible"
                ),
                None,
            )
            if not service:
                raise ValueError(
                    "Este servicio ya no está disponible. Recarga la página."
                )
            schedule = panel.record(c, "schedule_config", "schedule")
            if hour not in panel.slots(c, day):
                abort(
                    409,
                    description="Ese horario ya no está disponible. Selecciona otro.",
                )
            row = dict(
                client_name=name,
                phone=phone,
                email=email,
                service=service["name"],
                service_slug=service["slug"],
                people=people,
                location_type="external"
                if body["ubicacion"] == "Otra ubicación"
                else "studio",
                location=location or "Estudio de Tamara",
                notes=notes,
                event_date=day,
                event_time=hour,
                duration_minutes=schedule["appointment_duration"],
                duration_hours=schedule["appointment_duration"] / 60,
                status="pending",
                deposit_status="pending",
                deposit=0,
                total=round(service["price_amount"] * people, 2),
                exported_google=False,
                exported_apple=False,
                created=stamp,
                request_hash=fingerprint,
            )
            panel.put(c, "bookings", identity, row)
            c.execute("INSERT INTO attempts VALUES(?,?)", (scope, stamp))
        return jsonify(id=identity, status="pending"), 201
    except (ValueError, TypeError, KeyError, AttributeError):
        abort(
            400,
            description="Revisa nombre, contacto, servicio, fecha, hora y dirección. Usa texto simple y cantidades válidas.",
        )
