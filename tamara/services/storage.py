"""Private Supabase objects, served through the application's access checks."""
import io
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from flask import current_app, abort, send_file, send_from_directory
from ..database import on_rollback

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def _name(name):
    if not re.fullmatch(r"[a-f0-9]{32}(-thumb)?\.webp", name):
        raise ValueError("Nombre de imagen inválido.")
    return name

def _request(method, name, data=None):
    config = current_app.config
    bucket = quote(config["SUPABASE_STORAGE_BUCKET"], safe="")
    path = "object/authenticated" if method == "GET" else "object"
    url = f'{config["SUPABASE_URL"]}/storage/v1/{path}/{bucket}/{quote(_name(name), safe="")}'
    headers = {"apikey": config["SUPABASE_SECRET_KEY"]}
    if data is not None:
        headers["Content-Type"] = "image/webp"
    # Secret API keys go in apikey, never in a browser or a JWT bearer header.
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            result = response.read(12 * 1024 * 1024 + 1)
            if len(result) > 12 * 1024 * 1024:
                raise ValueError("Respuesta de almacenamiento demasiado grande.")
            return result
    except HTTPError as exc:
        missing = exc.code == 404
        exc.close()
        if missing and method == "DELETE":
            return b""
        if missing and method == "GET":
            abort(404)
        abort(503, description="No se pudo acceder al almacenamiento de fotos. Revisa la configuración de Supabase.")
    except (URLError, TimeoutError, OSError, ValueError):
        abort(503, description="El almacenamiento de fotos no está disponible. Intenta de nuevo.")

def delete(name):
    _name(name)
    if current_app.config["SUPABASE_URL"]:
        _request("DELETE", name)
    else:
        (current_app.config["DATA_DIR"] / "uploads" / name).unlink(missing_ok=True)

def save_pair(image, name):
    _name(name)
    width, height = image.size
    thumb = image.copy()
    thumb.thumbnail((480, 480))
    for filename, picture, quality in ((name, image, 85), (name.replace(".webp", "-thumb.webp"), thumb, 80)):
        # Register before upload: a timeout can happen after the server saved it.
        on_rollback(lambda filename=filename: delete(filename))
        if current_app.config["SUPABASE_URL"]:
            buffer = io.BytesIO()
            picture.save(buffer, "WEBP", quality=quality)
            _request("POST", filename, buffer.getvalue())
        else:
            picture.save(current_app.config["DATA_DIR"] / "uploads" / filename, "WEBP", quality=quality)
    return width, height

def serve(name):
    _name(name)
    if current_app.config["SUPABASE_URL"]:
        return send_file(io.BytesIO(_request("GET", name)), mimetype="image/webp", download_name=name, conditional=False)
    return send_from_directory(current_app.config["DATA_DIR"] / "uploads", name)
