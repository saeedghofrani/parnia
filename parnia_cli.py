"""Command-line and interactive entry point for Parnia."""

import argparse
import math
import os
import shutil
import sys
import time

from parnia_art import (ANIMATIONS, COLORS, STYLES, THEMES, animation_frames,
                        colorize, render_text, validate_pattern)


def _delay(value):
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("Delay must be from 0 to 1 seconds.")
    return number


def parser():
    cli = argparse.ArgumentParser(description="Parnia: a terminal art playground.")
    cli.add_argument("text", nargs="*", help="Words to draw; omit for interactive mode")
    cli.add_argument("-c", "--char", help="One visible drawing character; overrides theme")
    cli.add_argument("-s", "--scale", type=int, choices=range(1, 6), default=1)
    cli.add_argument("--theme", choices=THEMES, default="classic")
    cli.add_argument("--font", choices=STYLES, default="block", help="Letter style")
    cli.add_argument("--font-file", help="TrueType/OpenType font for Persian or rounded text")
    cli.add_argument("--message", help="Fill the letters with a repeating hidden message (no spaces)")
    cli.add_argument("--color", choices=COLORS, default="none")
    cli.add_argument("--animate", choices=ANIMATIONS, default="none")
    cli.add_argument("--delay", type=_delay, default=.06, help="Seconds per frame, 0 to 1")
    cli.add_argument("--image", help="Convert a local image into ASCII art")
    cli.add_argument("--width", type=int, default=80, help="Image width, 10 to 200 characters")
    cli.add_argument("--invert", action="store_true", help="Invert image brightness")
    cli.add_argument("--ramp", default="@%#*+=-:. ", help="Image characters from dark to light")
    cli.add_argument("--export", metavar="FILE", help="Save to .txt, .png or animated .gif")
    cli.add_argument("--overwrite", action="store_true", help="Replace an existing export")
    return cli


def _ansi_available():
    if not sys.stdout.isatty() or os.environ.get("TERM") == "dumb":
        return False
    if os.name == "nt":
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.GetStdHandle.restype = ctypes.c_void_p
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel.GetConsoleMode(ctypes.c_void_p(handle), ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(ctypes.c_void_p(handle), mode.value | 4))
    return True


def show_art(art, args):
    ansi = _ansi_available()
    palette = args.color if ansi else "none"
    size = shutil.get_terminal_size((80, 24))
    rows = art.split("\n")
    fits = len(rows) + 2 <= size.lines and max(map(len, rows), default=0) < size.columns
    if args.animate == "none" or not ansi or not fits:
        print(colorize(art, palette))
        return
    # Reserve room once, then return to that position instead of clearing the terminal.
    sys.stdout.write("\n" * len(rows) + f"\x1b[{len(rows)}A\x1b[s\x1b[?25l")
    try:
        for frame in animation_frames(art, args.animate):
            sys.stdout.write("\x1b[u" + "\n".join("\x1b[2K" + row
                             for row in colorize(frame, palette).split("\n")))
            sys.stdout.flush()
            time.sleep(args.delay)
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\n")
        sys.stdout.flush()


def _make_text(text, args):
    return render_text(text, args.char, args.scale, args.font,
                       args.theme, args.message, args.font_file)


def _deliver(art, args):
    if args.export:
        from parnia_media import export_art
        export_art(art, args.export, args.color,
                   "typewriter" if args.animate == "none" else args.animate,
                   args.delay, args.overwrite)
        print(f"Saved {args.export}", file=sys.stderr)
    show_art(art, args)


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.char is not None:
            from parnia import drawing_character
            drawing_character(args.char)
        if args.message is not None:
            validate_pattern(args.message)
        if args.image:
            if args.text:
                raise ValueError("Choose text or --image, not both.")
            if (args.message or args.char or args.theme != "classic" or args.font != "block"
                    or args.scale != 1 or args.font_file):
                raise ValueError("Image conversion uses --ramp; text font, theme and fill options do not apply.")
            from parnia_media import image_to_ascii
            _deliver(image_to_ascii(args.image, args.width, args.invert, args.ramp), args)
            return 0
        if args.invert or args.width != 80 or args.ramp != "@%#*+=-:. ":
            raise ValueError("Use --image with --width, --invert or --ramp.")
        if args.text:
            _deliver(_make_text(" ".join(args.text), args), args)
            return 0
        if not sys.stdin.isatty():
            text = sys.stdin.read(202)
            if len(text) > 201 or len(text.rstrip("\r\n")) > 200:
                raise ValueError("Use at most 200 characters.")
            # A single line ending from echo is transport, not another art block.
            _deliver(_make_text(text.rstrip("\r\n"), args), args)
            return 0
        print("Parnia | Terminal art playground. Type /quit to exit.")
        print(f"Style: {args.font} | Theme: {args.theme} | Color: {args.color} | Animation: {args.animate}")
        if args.char is None and args.theme == "classic" and args.message is None:
            args.char = input("Drawing character [#]: ") or "#"
            from parnia import drawing_character
            drawing_character(args.char)
        while True:
            text = input("\nText > ")
            if text.strip().lower() == "/quit":
                return 0
            try:
                _deliver(_make_text(text, args), args)
            except (ValueError, OSError) as error:
                print(f"Error: {error}", file=sys.stderr)
    except (EOFError, KeyboardInterrupt):
        return 0
    except (ValueError, OSError) as error:
        cli.error(str(error))
