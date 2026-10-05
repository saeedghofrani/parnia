"""Optional Pillow features: shaped text, image conversion and file exports."""

from pathlib import Path
import math
import os
import unicodedata
import warnings

from parnia_art import animation_frames, pixel_color, validate_pattern


def pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
    except ImportError as error:
        raise ValueError("This feature needs extras: python -m pip install -r requirements.txt") from error
    return Image, ImageDraw, ImageFont, ImageFilter, ImageOps


def load_font(size, path=None, *, mono=False, basic=False):
    _, _, ImageFont, _, _ = pillow()
    layout = ImageFont.Layout.BASIC if basic else None
    if path:
        try:
            return ImageFont.truetype(str(path), size, layout_engine=layout)
        except OSError as error:
            raise ValueError(f"Cannot load font: {path}") from error
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = ([windows / "consola.ttf", "DejaVuSansMono.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                   "/System/Library/Fonts/Menlo.ttc"] if mono else
                  [windows / "tahoma.ttf", "DejaVuSans.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/System/Library/Fonts/Supplemental/Arial.ttf"])
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size, layout_engine=layout)
        except OSError:
            continue
    if mono:
        return ImageFont.load_default(size=size)
    raise ValueError("No suitable font found. Supply --font-file /path/to/font.ttf (Persian needs Arabic glyphs).")


def shape_persian(text):
    try:
        from arabic_reshaper import ArabicReshaper
        from bidi.algorithm import get_display
    except ImportError as error:
        raise ValueError("Persian text needs extras: python -m pip install -r requirements.txt") from error
    reshaper = ArabicReshaper(configuration={"delete_harakat": False,
                                             "shift_harakat_position": True})
    return get_display(reshaper.reshape(text))


def text_bitmap(text, scale=1, font_path=None, persian=False):
    if not text.strip() or len(text) > 200:
        raise ValueError("Enter 1 to 200 characters of text.")
    if not isinstance(scale, int) or isinstance(scale, bool) or not 1 <= scale <= 5:
        raise ValueError("Scale must be an integer from 1 to 5.")
    if any(unicodedata.category(c).startswith("C") and c not in ("\n", "\u200c", "\u200d")
           for c in text):
        raise ValueError("Text cannot contain control characters.")
    Image, ImageDraw, _, _, _ = pillow()
    # Explicit BASIC layout avoids a second BiDi pass on already shaped text.
    font = load_font(32 if persian else 24, font_path, basic=True)
    blocks = []
    for line in text.split("\n"):
        line = shape_persian(line) if persian else line.upper()
        if not line:
            blocks.append("\n" * (12 * scale - 1))
            continue
        left, top, right, bottom = font.getbbox(line)
        image = Image.new("L", (max(1, right-left) + 4, max(1, bottom-top) + 4))
        ImageDraw.Draw(image).text((2-left, 2-top), line, font=font, fill=255)
        # Terminal cells are about twice as tall as they are wide.
        image = image.resize((image.width * scale, max(1, image.height * scale // 2)),
                             Image.Resampling.LANCZOS)
        blocks.append("\n".join("".join("#" if image.getpixel((x, y)) >= 80 else " "
                          for x in range(image.width)).rstrip() for y in range(image.height)))
    return "\n\n".join(blocks)


def image_to_ascii(path, width=80, invert=False, ramp="@%#*+=-:. "):
    if not isinstance(width, int) or not 10 <= width <= 200:
        raise ValueError("Image width must be from 10 to 200 characters.")
    if len(ramp) < 2 or len(ramp) > 100:
        raise ValueError("An image ramp needs 2 to 100 characters ordered dark to light.")
    for c in ramp:
        if c != " ":
            validate_pattern(c)
    Image, _, _, _, ImageOps = pillow()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                if source.width * source.height > 20_000_000:
                    raise ValueError("Use an image of at most 20 megapixels.")
                source = ImageOps.exif_transpose(source)
                rgba = source.convert("RGBA")
                background = Image.new("RGBA", rgba.size, "white")
                gray = Image.alpha_composite(background, rgba).convert("L")
                height = max(1, min(100, round(gray.height / gray.width * width * .5)))
                gray = gray.resize((width, height), Image.Resampling.LANCZOS)
                if invert:
                    gray = ImageOps.invert(gray)
                return "\n".join("".join(ramp[gray.getpixel((x, y)) * (len(ramp)-1) // 255]
                                     for x in range(width)).rstrip() for y in range(height))
    except (OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError(f"Cannot read image: {path}: {error}") from error


def _art_image(art, palette, width, height, font):
    Image, ImageDraw, _, ImageFilter, _ = pillow()
    image = Image.new("RGB", (width * 12 + 32, height * 20 + 32), (12, 15, 24))
    ink = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(ink)
    for y, row in enumerate(art.split("\n")):
        for x, char in enumerate(row):
            if char != " ":
                draw.text((16 + x*12, 16 + y*20), char, font=font,
                          fill=(*pixel_color(x, y, width, height, palette), 255))
    if palette == "neon":
        image = Image.alpha_composite(image.convert("RGBA"), ink.filter(ImageFilter.GaussianBlur(5)))
    return Image.alpha_composite(image.convert("RGBA"), ink).convert("RGB")


def export_art(art, path, palette="none", animation="typewriter", delay=.06,
               overwrite=False):
    from parnia_art import ANIMATIONS, COLORS
    if palette not in COLORS or animation not in ANIMATIONS:
        raise ValueError("Unknown palette or animation.")
    if not isinstance(delay, (int, float)) or not math.isfinite(delay) or not 0 <= delay <= 1:
        raise ValueError("Delay must be from 0 to 1 seconds.")
    target = Path(path)
    suffix = target.suffix.lower()
    if suffix not in (".txt", ".png", ".gif"):
        raise ValueError("Export filename must end in .txt, .png or .gif.")
    if target.exists() and not overwrite:
        raise ValueError(f"File already exists: {target}. Use --overwrite to replace it.")
    if not target.parent.is_dir():
        raise ValueError(f"Output directory does not exist: {target.parent}")
    if suffix == ".txt":
        target.write_text(art + "\n", encoding="utf-8")
        return
    rows = art.split("\n")
    width, height = max(1, max(map(len, rows), default=1)), max(1, len(rows))
    pixel_count = (width * 12 + 32) * (height * 20 + 32)
    if pixel_count > 4_000_000:
        raise ValueError("Art is too large for image export. Use less text, smaller scale or narrower image width.")
    font = load_font(17, mono=True)
    if suffix == ".png":
        _art_image(art, palette, width, height, font).save(target)
        return
    if animation == "none":
        raise ValueError("GIF export needs an animation: typewriter, pixels or fall.")
    count = min(24, max(2, 24_000_000 // pixel_count))
    frames = [_art_image(frame, palette, width, height, font)
              for frame in animation_frames(art, animation, count)]
    duration = max(20, round(delay*1000))
    frames[0].save(target, save_all=True, append_images=frames[1:], loop=0,
                   duration=[duration] * (len(frames)-1) + [1200], disposal=2)
