"""Validate the CMS schema before storing a draft."""

import re
from urllib.parse import urlsplit
from flask import request, abort
from .config import DEFAULT
from .database import db


def json_body():
    if not request.is_json:
        abort(415, description="Se requiere JSON.")
    value = request.get_json()
    if not isinstance(value, dict):
        abort(400, description="Datos inválidos.")
    return value


def text(value, maximum=5000):
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or "<" in value
        or ">" in value
        or "\x00" in value
    ):
        raise ValueError("Usa texto simple, sin HTML, de longitud permitida.")
    return value


def number(value, maximum=1_000_000):
    if type(value) not in (int, float) or not 0 <= value <= maximum:
        raise ValueError("Número fuera del rango permitido.")
    return value


def image_path(src, c):
    if isinstance(src, str) and src.lstrip("/") in DEFAULT["images"]:
        return src.lstrip("/")
    if (
        isinstance(src, str)
        and re.fullmatch(r"/media/[a-f0-9]{32}\.webp", src)
        and c.execute(
            "SELECT 1 FROM media WHERE id=?", (src.split("/")[-1],)
        ).fetchone()
    ):
        return src
    raise ValueError("Selecciona una imagen cargada o un placeholder original.")


def validate(data):
    if not isinstance(data, dict) or set(data) - {"_panel"} != set(DEFAULT):
        raise ValueError("Estructura de contenido incorrecta.")
    if set(data["texts"]) != set(DEFAULT["texts"]):
        raise ValueError("Faltan campos de contenido.")
    clean = {"texts": {k: text(v) for k, v in data["texts"].items()}}
    clean["seo"] = {
        k: text(data["seo"][k], 300 if k == "description" else 150)
        for k in DEFAULT["seo"]
    }
    theme = data["theme"]
    clean["theme"] = {}
    for k in DEFAULT["theme"]:
        v = theme[k]
        if k in ["font", "heading"]:
            from .services.reference_panel import FONT_NAMES

            if v not in FONT_NAMES:
                raise ValueError("Tipografía no permitida.")
        elif not isinstance(v, str) or not re.fullmatch("#[0-9a-fA-F]{6}", v):
            raise ValueError("Color inválido.")
        clean["theme"][k] = v
    settings = data["settings"]
    clean["settings"] = {}
    for k in DEFAULT["settings"]:
        v = settings[k]
        if k in ["base", "companion", "hair", "trial"]:
            v = number(v)
        elif k in ["whatsapp", "contactWhatsapp"]:
            if not isinstance(v, str) or (v and not re.fullmatch(r"[0-9]{8,15}", v)):
                raise ValueError("WhatsApp: usa de 8 a 15 dígitos con código de país.")
        else:
            v = text(v, 300)
            parts = urlsplit(v)
            if v and (
                parts.scheme != "https"
                or not parts.hostname
                or parts.username
                or parts.password
            ):
                raise ValueError("Las redes deben ser direcciones HTTPS completas.")
        clean["settings"][k] = v
    with db() as c:
        if not isinstance(data["images"], dict) or len(data["images"]) > 400:
            raise ValueError("Demasiadas imágenes.")
        clean["images"] = {}
        for key, v in data["images"].items():
            image_path(key, c)
            clean["images"][key] = {
                "src": image_path(v["src"], c),
                "alt": text(v["alt"], 250),
                "x": number(v["x"], 100),
                "y": number(v["y"], 100),
            }
        if not set(DEFAULT["images"]).issubset(clean["images"]):
            raise ValueError("Faltan imágenes originales.")
        services = data["services"]
        if not isinstance(services, list) or len(services) > 100:
            raise ValueError("Máximo 100 servicios.")
        clean["services"] = []
        slugs = set()
        for s in services:
            item = {
                k: text(s[k], 5000)
                for k in [
                    "slug",
                    "name",
                    "short",
                    "description",
                    "duration",
                    "price",
                ]
            }
            if (
                not re.fullmatch("[a-z0-9-]{1,60}", item["slug"])
                or item["slug"] in slugs
                or not item["name"].strip()
            ):
                raise ValueError(
                    "Cada servicio necesita un identificador único y un nombre."
                )
            slugs.add(item["slug"])
            item["price_amount"] = number(s["price_amount"])
            if s["status"] not in ["visible", "hidden", "archived"]:
                raise ValueError("Estado inválido.")
            item["status"] = s["status"]
            # Preserve the quiz association when an administrator renames a service slug.
            if "quiz_slug" in s:
                if s["quiz_slug"] not in ("novia", "eventos", "social", "editorial"):
                    raise ValueError("Asociación del quiz inválida.")
                item["quiz_slug"] = s["quiz_slug"]
            if not isinstance(s["includes"], list) or len(s["includes"]) > 50:
                raise ValueError("Máximo 50 elementos incluidos.")
            item["includes"] = [text(v, 300) for v in s["includes"]]
            if not isinstance(s["images"], list) or len(s["images"]) > 40:
                raise ValueError("Máximo 40 fotos por servicio.")
            item["images"] = [image_path(v, c) for v in s["images"]]
            if any(v not in clean["images"] for v in item["images"]):
                raise ValueError("Faltan metadatos de imágenes.")
            if type(s["cover_index"]) is not int or not 0 <= s["cover_index"] < max(
                1, len(item["images"])
            ):
                raise ValueError("Selecciona una portada válida.")
            item["cover_index"] = s["cover_index"]
            clean["services"].append(item)
    return clean
