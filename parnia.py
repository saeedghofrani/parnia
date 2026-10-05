"""Parnia: turn text into simple terminal art, without dependencies."""

import unicodedata


# Five-column, seven-row bitmap font. Lowercase input uses uppercase glyphs.
_PATTERNS = {
    "A": "01110 10001 10001 11111 10001 10001 10001",
    "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01111 10000 10000 10000 10000 10000 01111",
    "D": "11110 10001 10001 10001 10001 10001 11110",
    "E": "11111 10000 10000 11110 10000 10000 11111",
    "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01111 10000 10000 10111 10001 10001 01111",
    "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "11111 00100 00100 00100 00100 00100 11111",
    "J": "00111 00010 00010 00010 10010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001",
    "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001",
    "N": "10001 11001 10101 10011 10001 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110",
    "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101",
    "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110",
    "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110",
    "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 10101 01010",
    "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100",
    "Z": "11111 00001 00010 00100 01000 10000 11111",
    "0": "01110 10001 10011 10101 11001 10001 01110",
    "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111",
    "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010",
    "5": "11111 10000 10000 11110 00001 00001 11110",
    "6": "01110 10000 10000 11110 10001 10001 01110",
    "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110",
    "9": "01110 10001 10001 01111 00001 00001 01110",
    " ": "00000 00000 00000 00000 00000 00000 00000",
    ".": "00000 00000 00000 00000 00000 00100 00100",
    ",": "00000 00000 00000 00000 00100 00100 01000",
    "!": "00100 00100 00100 00100 00100 00000 00100",
    "?": "01110 10001 00001 00010 00100 00000 00100",
    "-": "00000 00000 00000 11111 00000 00000 00000",
    "_": "00000 00000 00000 00000 00000 00000 11111",
    ":": "00000 00100 00100 00000 00100 00100 00000",
    "/": "00001 00001 00010 00100 01000 10000 10000",
    "+": "00000 00100 00100 11111 00100 00100 00000",
    "'": "00100 00100 00000 00000 00000 00000 00000",
}
FONT = {letter: pattern.split() for letter, pattern in _PATTERNS.items()}


def drawing_character(value):
    """Require one printable, single-width terminal character."""
    if (len(value) != 1 or value.isspace() or not value.isprintable()
            or unicodedata.category(value).startswith("M")
            or unicodedata.east_asian_width(value) in ("W", "F")):
        raise ValueError("Choose one visible, single-width character, such as #, ., 1, _ or -.")
    return value


def render(text, character="#", scale=1):
    """Render supported text; reject unknown symbols instead of hiding them."""
    drawing_character(character)
    if not isinstance(scale, int) or isinstance(scale, bool) or not 1 <= scale <= 5:
        raise ValueError("Scale must be an integer from 1 to 5.")
    text = text.upper()
    if not text.strip():
        raise ValueError("Enter some text to draw.")
    if len(text) > 200:
        raise ValueError("Use at most 200 characters.")
    unsupported = sorted(set(text) - set(FONT) - {"\n"})
    if unsupported:
        raise ValueError("Unsupported characters: " + ", ".join(repr(c) for c in unsupported)
                         + ". Use English letters, numbers or common punctuation.")
    blocks = []
    for line in text.split("\n"):
        rows = []
        for row in range(7):
            pixels = (" " * (2 * scale)).join(
                "".join((character if bit == "1" else " ") * scale
                        for bit in FONT[letter][row]) for letter in line)
            rows.extend([pixels.rstrip()] * scale)
        blocks.append("\n".join(rows))
    return "\n\n".join(blocks)


def main(argv=None):
    # Lazy import keeps the original renderer usable with just Python.
    from parnia_cli import main as run
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
