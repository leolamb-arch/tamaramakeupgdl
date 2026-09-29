"""Typed validation of the public settings consumed by JavaScript and HTML."""

import copy
import re
from urllib.parse import urlsplit
from .validation import text, number


def shape(value, template, path="configuración"):
    if isinstance(template, str):
        return text(value)
    if type(template) is bool:
        if type(value) is not bool:
            raise ValueError(f"{path}: se necesita verdadero o falso.")
        return value
    if type(template) in (int, float):
        return number(value)
    if isinstance(template, dict):
        if not isinstance(value, dict) or set(template) - set(value):
            raise ValueError(f"{path}: faltan campos obligatorios.")
        if set(value) - set(template):
            raise ValueError(f"{path}: hay campos desconocidos.")
        return {
            key: shape(value[key], item, f"{path}.{key}")
            for key, item in template.items()
        }
    if not isinstance(value, list) or len(value) > 100:
        raise ValueError(f"{path}: lista inválida (máximo 100).")
    return [shape(item, template[0], path) for item in value] if template else value


def validate_typed(collection, value, c):
    from .services.reference_panel import REFERENCE, TEXT_MAP, local_image

    if collection == "services":
        for key in ("slug", "name", "short", "description", "duration", "price"):
            text(value.get(key, ""))
        for key, maximum in [("cover_index", 39), ("sort_order", 10000)]:
            if (
                type(value.get(key, 0)) is not int
                or not 0 <= value.get(key, 0) <= maximum
            ):
                raise ValueError(f"{key}: usa un número entero válido.")
        for key, limit in [("images", 40), ("includes", 50)]:
            if (
                not isinstance(value.get(key, []), list)
                or len(value.get(key, [])) > limit
            ):
                raise ValueError(f"{key}: demasiados elementos o formato inválido.")
        for item in value.get("includes", []):
            text(item, 300)
    elif collection == "appearance":
        shape(value.get("data"), REFERENCE["yr"])
        for key in ("logo_alt", "hero_image_alt"):
            text(value.get(key, ""), 250)
    elif collection == "site_content":
        template = copy.deepcopy(REFERENCE["rr"])
        template.update({key: "" for key in TEXT_MAP})
        site = value.get("data")
        if not isinstance(site, dict):
            raise ValueError("Contenido inválido.")
        basic = {
            key: item for key, item in site.items() if key not in ("calculator", "quiz")
        }
        shape(basic, template)
        calc = site.get("calculator")
        if isinstance(calc, dict):
            for key in ("basePrice", "perPerson"):
                if isinstance(calc.get(key), str):
                    calc[key] = number(float(calc[key]))
        shape(calc, REFERENCE["Nt"])
        if not re.fullmatch("[A-Z]{3}", calc["currency"]["code"]) or not re.fullmatch(
            "[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{2,8})*", calc["currency"]["locale"]
        ):
            raise ValueError("Moneda o idioma inválido.")
        unique(calc["addons"], "id")
        quiz = site.get("quiz")
        if not isinstance(quiz, dict) or set(quiz) != {
            "questions",
            "texts",
            "extrasNote",
        }:
            raise ValueError("Configuración del quiz inválida.")
        shape(quiz["texts"], REFERENCE["Vd"])
        if (
            not isinstance(quiz["questions"], list)
            or not 1 <= len(quiz["questions"]) <= 20
        ):
            raise ValueError("El quiz necesita entre 1 y 20 preguntas.")
        unique(quiz["questions"], "id")
        for question in quiz["questions"]:
            if set(question) != {"id", "question", "options"}:
                raise ValueError("Pregunta inválida.")
            text(question["id"], 100)
            text(question["question"])
            options = question["options"]
            if not isinstance(options, list) or not 1 <= len(options) <= 50:
                raise ValueError("Cada pregunta necesita entre 1 y 50 opciones.")
            unique(options, "id")
            for option in options:
                if (
                    not isinstance(option, dict)
                    or not {"id", "label"} <= set(option)
                    or set(option) - {"id", "label", "service"}
                ):
                    raise ValueError("Opción inválida.")
                for item in option.values():
                    text(item, 300)
        if not isinstance(quiz["extrasNote"], dict):
            raise ValueError("Notas del quiz inválidas.")
        for key, item in quiz["extrasNote"].items():
            text(key, 100)
            text(item)
        for url in site["socials"].values():
            parsed = urlsplit(url)
            if url and (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError("Usa enlaces HTTPS completos, sin credenciales.")
        if site["email"] and not re.fullmatch(
            r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", site["email"]
        ):
            raise ValueError("Correo electrónico inválido.")
        for key in ("main", "detail"):
            if site["heroImages"][key]:
                local_image(site["heroImages"][key], c)
    return value


def unique(rows, key):
    identifiers = [text(row[key], 100) for row in rows]
    if any(not item for item in identifiers) or len(set(identifiers)) != len(
        identifiers
    ):
        raise ValueError("Los identificadores deben ser únicos y no vacíos.")
