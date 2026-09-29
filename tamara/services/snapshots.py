"""Version the public CMS and its panel projection together; never include bookings."""

import copy
from . import reference_panel as panel

COLLECTIONS = ("site_content", "appearance", "services")


def capture(c, data):
    value = copy.deepcopy(data)
    if "_panel" not in value:
        value["_panel"] = {name: panel.records(c, name) for name in COLLECTIONS}
    return value


def project(c, data, source=None):
    """Project edits from the complete text editor into the reference panel."""
    value = copy.deepcopy(data)
    snapshot = copy.deepcopy((source or {}).get("_panel") or capture(c, {})["_panel"])
    site = snapshot["site_content"][0]["data"]
    site.update({key: value["texts"][field] for key, field in panel.TEXT_MAP.items()})
    site["whatsapp"] = value["settings"]["whatsapp"]
    site["socials"].update(
        {key: value["settings"][key] for key in ("instagram", "facebook", "tiktok")}
    )
    site["socials"]["whatsapp"] = (
        "https://wa.me/" + value["settings"]["contactWhatsapp"]
        if value["settings"]["contactWhatsapp"]
        else ""
    )
    for section, mapping in [("calculator", panel.CALC_MAP), ("quiz", panel.QUIZ_MAP)]:
        site[section]["texts"].update(
            {key: value["texts"][field] for key, field in mapping.items()}
        )
    calc = site["calculator"]
    calc.update(
        basePrice=value["settings"]["base"], perPerson=value["settings"]["companion"]
    )
    for addon in calc["addons"]:
        if addon["id"] in ("peinado", "prueba"):
            addon["price"] = value["settings"][
                "hair" if addon["id"] == "peinado" else "trial"
            ]
    for i, item in enumerate(site["testimonials"][:3]):
        for field, key in [
            ("name", f"t{88 + i * 3:03}"),
            ("event", f"t{89 + i * 3:03}"),
        ]:
            if not source or value["texts"][key] != source["texts"][key]:
                item[field] = value["texts"][key]
        key = [
            "assets/testimonio-mariana.svg",
            "assets/testimonio-fernanda.svg",
            "assets/testimonio-alejandra.svg",
        ][i]
        if not source or value["images"][key]["src"] != source["images"][key]["src"]:
            item["photo"] = "/" + value["images"][key]["src"].lstrip("/")
    appearance = snapshot["appearance"][0]
    appearance["data"].update(
        titleFont=value["theme"]["heading"],
        bodyFont="Modern"
        if value["theme"]["font"] == "Outfit"
        else value["theme"]["font"],
    )
    for key in appearance["data"]["colors"]:
        if key in value["theme"]:
            appearance["data"]["colors"][key] = panel.hex_hsl(value["theme"][key])
    if source and value["theme"]["primary"] != source["theme"]["primary"]:
        appearance["data"]["colors"]["button"] = panel.hex_hsl(
            value["theme"]["primary"]
        )
    for field, key in [
        ("logo", "assets/logo-placeholder.svg"),
        ("hero_image", "assets/portada-retrato.svg"),
    ]:
        appearance[field] = "/" + value["images"][key]["src"].lstrip("/")
        appearance[field + "_alt"] = value["images"][key]["alt"]
    existing = {s["slug"]: s for s in snapshot["services"]}
    services = []
    for order, service in enumerate(value["services"]):
        previous = existing.get(service["slug"], {})
        services.append(
            {
                **service,
                "id": previous.get("id", service["slug"]),
                "active": service["status"] == "visible",
                "sort_order": order,
                "images": [
                    "/" + value["images"][k]["src"].lstrip("/")
                    for k in service["images"]
                ],
            }
        )
    snapshot["services"] = services
    value["_panel"] = snapshot
    return value


def install(c, data):
    value = copy.deepcopy(data) if "_panel" in data else project(c, data)
    for collection, rows in value["_panel"].items():
        if collection not in COLLECTIONS:
            continue
        existing = {r["id"]: r for r in panel.records(c, collection)}
        for row in rows:
            identity = row["id"]
            panel.put(
                c,
                collection,
                identity,
                row,
                existing.get(identity, {}).get("_version", 0) + 1,
            )
        for identity in existing.keys() - {r["id"] for r in rows}:
            c.execute(
                "DELETE FROM panel_records WHERE collection=? AND id=?",
                (collection, identity),
            )
    value.pop("_panel", None)
    return capture(c, value)
