"""Art styles, palettes and deterministic animation frames (standard library)."""

import colorsys
import math
import random

from parnia import drawing_character, render

THEMES = {"classic": "#", "dots": ".", "binary": "01", "hearts": "♥", "stars": "*"}
STYLES = ("block", "tiny", "bold", "rounded", "outline", "shadow")
COLORS = ("none", "rainbow", "gradient", "neon")
ANIMATIONS = ("none", "typewriter", "pixels", "fall")

_TINY = {
    "A": "010 101 111 101 101", "B": "110 101 110 101 110",
    "C": "011 100 100 100 011", "D": "110 101 101 101 110",
    "E": "111 100 110 100 111", "F": "111 100 110 100 100",
    "G": "011 100 101 101 011", "H": "101 101 111 101 101",
    "I": "111 010 010 010 111", "J": "001 001 001 101 010",
    "K": "101 101 110 101 101", "L": "100 100 100 100 111",
    "M": "101 111 111 101 101", "N": "101 111 111 111 101",
    "O": "010 101 101 101 010", "P": "110 101 110 100 100",
    "Q": "010 101 101 111 011", "R": "110 101 110 101 101",
    "S": "011 100 010 001 110", "T": "111 010 010 010 010",
    "U": "101 101 101 101 111", "V": "101 101 101 101 010",
    "W": "101 101 111 111 101", "X": "101 101 010 101 101",
    "Y": "101 101 010 010 010", "Z": "111 001 010 100 111",
    "0": "111 101 101 101 111", "1": "010 110 010 010 111",
    "2": "110 001 010 100 111", "3": "110 001 010 001 110",
    "4": "101 101 111 001 001", "5": "111 100 110 001 110",
    "6": "011 100 111 101 111", "7": "111 001 010 010 010",
    "8": "111 101 111 101 111", "9": "111 101 111 001 110",
    " ": "000 000 000 000 000", ".": "000 000 000 000 010",
    ",": "000 000 000 010 100", "!": "010 010 010 000 010",
    "?": "110 001 010 000 010", "-": "000 000 111 000 000",
    "_": "000 000 000 000 111", ":": "000 010 000 010 000",
    "/": "001 001 010 100 100", "+": "000 010 111 010 000",
    "'": "010 010 000 000 000",
}


def validate_pattern(pattern):
    if not pattern or len(pattern) > 100:
        raise ValueError("A fill message must contain 1 to 100 visible characters.")
    for char in pattern:
        drawing_character(char)
    return pattern


def _tiny(text, scale):
    blocks = []
    for line in text.upper().split("\n"):
        rows = []
        for y in range(5):
            row = (" " * scale).join("".join(("#" if p == "1" else " ") * scale
                    for p in _TINY[c].split()[y]) for c in line)
            rows.extend([row.rstrip()] * scale)
        blocks.append("\n".join(rows))
    return "\n\n".join(blocks)


def _style(art, style):
    rows = art.split("\n")
    width = max(map(len, rows), default=0)
    grid = [row.ljust(width) for row in rows]
    if style == "bold":
        return "\n".join("".join(c * 2 for c in row).rstrip() for row in grid)
    if style == "outline":
        def edge(x, y):
            return any(nx < 0 or ny < 0 or nx >= width or ny >= len(grid)
                       or grid[ny][nx] == " "
                       for nx, ny in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)))
        return "\n".join("".join(c if c != " " and edge(x, y) else " "
                         for x, c in enumerate(row)).rstrip() for y, row in enumerate(grid))
    if style == "shadow":
        result = [[" "] * (width + 2) for _ in range(len(grid) + 1)]
        for y, row in enumerate(grid):
            for x, c in enumerate(row):
                if c != " ":
                    result[y+1][x+2] = "."
        for y, row in enumerate(grid):
            for x, c in enumerate(row):
                if c != " ":
                    result[y][x] = c
        return "\n".join("".join(row).rstrip() for row in result)
    return art


def render_text(text, character=None, scale=1, style="block", theme="classic",
                message=None, font_path=None):
    if style not in STYLES or theme not in THEMES:
        raise ValueError("Unknown font style or character theme.")
    pattern = validate_pattern(message if message is not None else
                               character if character is not None else THEMES[theme])
    persian = any("\u0600" <= c <= "\u06ff" for c in text)
    if persian and style == "tiny":
        raise ValueError("Tiny uses an English bitmap font. Choose block, rounded, bold, outline or shadow for Persian.")
    if font_path and not (persian or style == "rounded"):
        raise ValueError("Use --font-file with rounded style or Persian text.")
    if persian or style == "rounded":
        from parnia_media import text_bitmap
        base = text_bitmap(text, scale, font_path, persian)
    else:
        base = render(text, "#", scale)  # Shared input validation.
        if style == "tiny":
            base = _tiny(text, scale)
    base = _style(base, style)
    index = 0
    output = []
    for c in base:
        if c not in (" ", "\n") and not (style == "shadow" and c == "."):
            output.append(pattern[index % len(pattern)])
            index += 1
        else:
            output.append(c)
    return "".join(output)


def pixel_color(x, y, width, height, palette):
    if palette == "rainbow":
        return tuple(round(v * 255) for v in colorsys.hsv_to_rgb(
            ((x / max(1, width)) + y / max(1, height) * .12) % 1, .8, 1))
    t = x / max(1, width - 1)
    if palette == "gradient":
        return tuple(round(a + (b-a)*t) for a, b in zip((255, 90, 160), (75, 200, 255)))
    if palette == "neon":
        return (90, 255, 190)
    return (235, 240, 250)


def colorize(art, palette):
    if palette not in COLORS:
        raise ValueError("Unknown color palette.")
    if palette == "none":
        return art
    rows = art.split("\n")
    width = max(map(len, rows), default=1)
    return "\n".join("".join(
        f"\x1b[38;2;{r};{g};{b}m{c}\x1b[0m" if c != " " else c
        for x, c in enumerate(row)
        for r, g, b in [pixel_color(x, y, width, len(rows), palette)])
        for y, row in enumerate(rows))


def animation_frames(art, effect="typewriter", count=24):
    """Bounded frames with stable dimensions and an exact final frame."""
    if effect not in ANIMATIONS:
        raise ValueError("Unknown animation effect.")
    if not isinstance(count, int) or not 2 <= count <= 48:
        raise ValueError("Frame count must be from 2 to 48.")
    if effect == "none":
        return [art]
    rows = art.split("\n")
    width, height = max(map(len, rows), default=0), len(rows)
    coords = [(x, y, c) for y, row in enumerate(rows) for x, c in enumerate(row) if c != " "]
    if effect == "pixels":
        random.Random(42).shuffle(coords)
    frames = []
    for i in range(count - 1):
        progress = i / (count - 1)
        canvas = [[" "] * width for _ in rows]
        for j, (x, y, c) in enumerate(coords):
            if effect == "fall":
                delay = (x % 7) / 20
                p = max(0, min(1, (progress-delay) / (1-delay)))
                target_y = y - math.ceil((1-p) ** 2 * height)
                if target_y >= 0:
                    canvas[target_y][x] = c
            elif (effect == "typewriter" and x < int(width * progress)) or (
                    effect == "pixels" and j < int(len(coords) * progress)):
                canvas[y][x] = c
        frames.append("\n".join("".join(row).rstrip() for row in canvas))
    frames.append(art)
    return frames
