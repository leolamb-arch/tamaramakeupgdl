"""Decode and sanitize new uploads; existing files are never re-encoded."""

import io
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from flask import abort

Image.MAX_IMAGE_PIXELS = 24_000_000


def decode_image(raw):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            im = Image.open(io.BytesIO(raw))
            if (
                im.format not in ["JPEG", "PNG", "WEBP"]
                or getattr(im, "n_frames", 1) != 1
            ):
                raise ValueError()
            if (
                min(im.size) < 32
                or max(im.size) > 10000
                or im.width * im.height > 24_000_000
            ):
                raise ValueError()
            im.verify()
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
            im.load()
            im = im.convert(
                "RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB"
            )
            # Re-encode pixels only: discard metadata, filenames and appended payloads.
            clean = Image.new(im.mode, im.size)
            clean.paste(im)
            clean.thumbnail((2400, 2400))
    except (
        ValueError,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        abort(
            400,
            description="Imagen inválida. Usa JPEG, PNG o WebP estático, de 32 a 10000 px y hasta 24 megapíxeles.",
        )
    return clean
