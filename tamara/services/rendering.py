"""Render stored content without trusting it as HTML."""

import json
from functools import lru_cache
from bs4 import BeautifulSoup
from ..config import ROOT, DEFAULT
from .content import public_content
from .reference_panel import public_settings


def render_public(packed):
    """Reuse only public snapshots; changes of content/template invalidate the cache."""
    stamp = (ROOT / "templates/public/index.html").stat().st_mtime_ns
    return _render_public(packed, stamp, json.dumps(public_settings(),ensure_ascii=False))


@lru_cache(maxsize=4)
def _render_public(packed, template_stamp, panel_packed):
    return render(json.loads(packed), panel_data=json.loads(panel_packed))


def render(data, preview=False, panel_data=None):
    data = public_content(data)
    data['panel']=public_settings() if panel_data is None else panel_data
    soup = BeautifulSoup(
        (ROOT / "templates/public/index.html").read_text(encoding="utf-8"),
        "html.parser",
    )
    for tag in soup.select("[data-cms]"):
        tag.string = data["texts"][tag["data-cms"]]
        tag.unwrap()
    soup.title.string = data["seo"]["title"]
    soup.select_one("meta[name=description]")["content"] = data["seo"]["description"]
    for img in soup.select("img[data-image]"):
        v = data["images"][img["data-image"]]
        img["src"] = v["src"]
        img["alt"] = v["alt"]
        img["style"] = f"object-position:{v['x']}% {v['y']}%"
    theme = data["theme"]
    style = soup.new_tag("style")
    style.string = (
        ":root{"
        + "".join(
            f"--{k}:{v};" for k, v in theme.items() if k not in ["font", "heading"]
        )
        + '}body{font-family:"'
        + theme["font"]
        + '",sans-serif}h1,h2,h3{font-family:"'
        + theme["heading"]
        + '",serif}header{background:color-mix(in srgb,var(--background) 85%,transparent)}'
    )
    soup.head.append(style)
    if data['panel'].get('appearance'):
        fonts=soup.new_tag('link',rel='stylesheet',href='/reference-assets/all-fonts.css')
        soup.head.append(fonts)
    dynamic_defaults = {
        k: DEFAULT["texts"][k] for k in ("t068", "t074", "t076", "t102")
    }
    data["dynamic_defaults"] = dynamic_defaults
    script = soup.new_tag("script", id="cms-data", type="application/json")
    script.string = (
        json.dumps(data, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    soup.head.append(script)
    if preview:
        banner = soup.new_tag("p")
        banner["style"] = (
            "position:fixed;bottom:0;left:0;z-index:100;background:#fff;padding:8px;margin:0"
        )
        banner.string = "Vista previa privada · borrador sin publicar"
        soup.body.append(banner)
    return str(soup)
