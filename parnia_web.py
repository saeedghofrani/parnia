"""Local web studio. Uploaded photos and generated downloads are transient."""

import io
import json
import math
import re
import tempfile
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException

from parnia_art import ANIMATIONS, COLORS, STYLES, THEMES, animation_frames, render_text
from parnia_media import export_art, image_to_ascii

ROOT = Path(__file__).resolve().parent
BORDERS = {"single": ("+", "+", "+", "+", "-", "|"),
           "double": ("╔", "╗", "╚", "╝", "═", "║"),
           "rounded": ("╭", "╮", "╰", "╯", "─", "│")}


def _number(data, name, default, low, high, integer=False):
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a number.")
    if not low <= value <= high or (integer and int(value) != value):
        raise ValueError(f"{name} must be {'an integer ' if integer else ''}from {low} to {high}.")
    return int(value) if integer else value


def _choice(data, name, default, choices):
    value = data.get(name, default)
    if value not in choices:
        raise ValueError(f"Invalid {name}.")
    return value


def _boolean(data, name):
    value = data.get(name, False)
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be true or false.")
    return value


def _hex(data, name, default):
    value = data.get(name, default)
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError(f"Invalid {name} color.")
    return value


def decorate(art, border="none", padding=1, alignment="center"):
    blocks = art.split("\n\n")
    width = max((len(row) for row in art.split("\n")), default=0)
    rows = []
    for i, block in enumerate(blocks):
        block_width = max(map(len, block.split("\n")), default=0)
        offset = 0 if alignment == "left" else width-block_width if alignment == "right" else (width-block_width)//2
        rows.extend(" " * offset + row for row in block.split("\n"))
        if i < len(blocks)-1:
            rows.append("")
    if border == "none":
        return "\n".join(row.rstrip() for row in rows)
    tl, tr, bl, br, horizontal, vertical = BORDERS[border]
    inner = width + 2*padding
    return "\n".join([tl + horizontal*inner + tr] +
        [vertical + " "*inner + vertical]*padding +
        [vertical + " "*padding + row.ljust(width) + " "*padding + vertical for row in rows] +
        [vertical + " "*inner + vertical]*padding + [bl + horizontal*inner + br])


def create_app():
    app = Flask(__name__, template_folder=str(ROOT / "web/templates"),
                static_folder=str(ROOT / "web/static"))
    app.config.update(MAX_CONTENT_LENGTH=8*1024*1024, MAX_FORM_MEMORY_SIZE=256*1024)
    gate = threading.BoundedSemaphore(2)

    @app.before_request
    def same_origin():
        if request.method == "POST":
            origin = request.headers.get("Origin")
            if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
                return jsonify(error="Cross-origin requests are not allowed."), 403

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' blob: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error="Upload is too large. Maximum is 8 MB." if error.code == 413
                       else error.description), error.code

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok", app="Parnia")

    @app.get("/api/options")
    def options():
        return jsonify(themes=list(THEMES), fonts=STYLES, colors=COLORS, animations=ANIMATIONS)

    @app.post("/api/render")
    def generate():
        if not gate.acquire(blocking=False):
            return jsonify(error="The studio is busy. Try again in a moment."), 429
        try:
            if request.is_json:
                data = request.get_json()
            else:
                data = json.loads(request.form.get("options", "{}"))
            if not isinstance(data, dict):
                raise ValueError("Options must be an object.")
            mode = _choice(data, "mode", "text", ("text", "image"))
            palette = _choice(data, "color", "none", COLORS)
            effect = _choice(data, "animation", "none", ANIMATIONS)
            background = _hex(data, "background", "#0c0f18")
            foreground = _hex(data, "foreground", "#ebf0fa")
            border = _choice(data, "border", "none", ("none", *BORDERS))
            alignment = _choice(data, "alignment", "center", ("left", "center", "right"))
            padding = _number(data, "padding", 1, 0, 4, True)
            delay = _number(data, "delay", .06, .02, .5)
            output = _choice(data, "output", "preview", ("preview", "txt", "png", "gif"))
            if mode == "text":
                text = data.get("text", "Parnia")
                character, message = data.get("character") or None, data.get("message") or None
                if not isinstance(text, str) or any(value is not None and not isinstance(value, str)
                        for value in (character, message)):
                    raise ValueError("Text and fill options must be strings.")
                style = _choice(data, "font", "block", STYLES)
                theme = _choice(data, "theme", "classic", THEMES)
                scale = _number(data, "scale", 1, 1, 5, True)
                art = render_text(text, character, scale, style, theme, message)
            else:
                upload = request.files.get("image")
                if not upload:
                    raise ValueError("Choose a photo first.")
                image_bytes = upload.read(8*1024*1024 + 1)
                if len(image_bytes) > 8*1024*1024:
                    raise ValueError("Upload is too large. Maximum is 8 MB.")
                ramp = data.get("ramp", "@%#*+=-:. ")
                if not isinstance(ramp, str):
                    raise ValueError("Character ramp must be a string.")
                art = image_to_ascii(io.BytesIO(image_bytes),
                    _number(data, "width", 100, 10, 200, True), _boolean(data, "invert"), ramp,
                    _number(data, "brightness", 1, .2, 3), _number(data, "contrast", 1, .2, 3),
                    _boolean(data, "edges"), _boolean(data, "mirror"))
            art = decorate(art, border, padding, alignment)
            rows = art.split("\n")
            width = max(map(len, rows), default=0)
            if len(art) > 80_000:
                raise ValueError("Art is too large for the web studio. Reduce text length or scale.")
            if output == "preview":
                frames = animation_frames(art, effect, count=24)
                return jsonify(art=art, frames=frames, width=width, height=len(rows),
                               color=palette, background=background, foreground=foreground,
                               delay=delay, animation=effect)
            if output == "txt":
                content = io.BytesIO((art + "\n").encode("utf-8"))
            else:
                with tempfile.TemporaryDirectory(prefix="parnia-") as folder:
                    target = Path(folder) / f"parnia.{output}"
                    export_art(art, target, palette, effect if effect != "none" else "typewriter",
                               delay, background=background, foreground=foreground)
                    content = io.BytesIO(target.read_bytes())
            return send_file(content, download_name=f"parnia.{output}", as_attachment=True,
                             mimetype={"txt": "text/plain; charset=utf-8", "png": "image/png", "gif": "image/gif"}[output])
        except (ValueError, TypeError) as error:
            return jsonify(error=str(error)), 400
        finally:
            gate.release()

    return app


app = create_app()
