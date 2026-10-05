import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from parnia import render
from parnia_art import animation_frames, colorize, render_text
from parnia_cli import main, parser, show_art

HAS_EXTRAS = all(importlib.util.find_spec(module) for module in ("PIL", "arabic_reshaper", "bidi"))


class PlaygroundTests(unittest.TestCase):
    def test_themes_and_explicit_character(self):
        for theme, allowed in (("dots", "."), ("binary", "01"), ("hearts", "♥"), ("stars", "*")):
            with self.subTest(theme=theme):
                art = render_text("Parnia", theme=theme)
                self.assertTrue(set(art) - {" ", "\n"} <= set(allowed))
                self.assertTrue(set(art) & set(allowed))
        self.assertEqual(render_text("P", "#", theme="binary"), render("P"))

    def test_hidden_message_follows_occupied_pixels(self):
        art = render_text("P", message="hello")
        letters = "".join(c for c in art if not c.isspace())
        self.assertEqual(letters, ("hello" * len(letters))[:len(letters)])
        self.assertEqual([[c.isspace() for c in row] for row in art.splitlines()],
                         [[c.isspace() for c in row] for row in render("P").splitlines()])

    def test_font_styles(self):
        self.assertEqual(len(render_text("ABC", style="tiny").splitlines()), 5)
        self.assertGreater(len(render_text("P", style="bold").splitlines()[0]),
                           len(render_text("P").splitlines()[0]))
        self.assertIn(".", render_text("P", style="shadow"))
        solid = render_text("I", scale=3)
        outline = render_text("I", scale=3, style="outline")
        self.assertLess(outline.count("#"), solid.count("#"))

    def test_animation_frames(self):
        art = render("Parnia")
        for effect in ("pixels", "typewriter", "fall"):
            with self.subTest(effect=effect):
                frames = animation_frames(art, effect, count=12)
                self.assertEqual(len(frames), 12)
                self.assertEqual(frames[-1], art)
                self.assertEqual(len(frames[0].replace("\n", "").strip()), 0)
                self.assertTrue(all(len(frame.split("\n")) == 7 for frame in frames))
                self.assertEqual(frames, animation_frames(art, effect, count=12))
        self.assertEqual(animation_frames(art, "none"), [art])
        self.assertNotEqual(animation_frames(art, "typewriter")[12],
                            animation_frames(art, "pixels")[12])

    def test_color_and_redirected_output(self):
        art = render("P")
        for palette in ("rainbow", "gradient", "neon"):
            self.assertIn("\x1b[38;2;", colorize(art, palette))
        args = parser().parse_args(["--color", "rainbow", "--animate", "fall"])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            show_art(art, args)
        self.assertEqual(output.getvalue(), art + "\n")

    def test_live_animation_restores_cursor(self):
        args = parser().parse_args(["--animate", "pixels", "--delay", "0"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch("parnia_cli._ansi_available", return_value=True):
            show_art(render("P"), args)
        self.assertIn("\x1b[?25l", output.getvalue())
        self.assertTrue(output.getvalue().endswith("\x1b[0m\x1b[?25h\n"))

    def test_interactive_flow(self):
        stdin = io.StringIO()
        stdin.isatty = lambda: True
        output, errors = io.StringIO(), io.StringIO()
        with patch("sys.stdin", stdin), patch("builtins.input", side_effect=[".", "", "Parnia", "/quit"]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(main([]), 0)
        self.assertIn(render("Parnia", "."), output.getvalue())
        self.assertIn("Enter some text", errors.getvalue())

    def test_invalid_flags_and_long_stdin(self):
        for flags in (["P", "--delay", "nan"], ["P", "--message", "a b"],
                      ["P", "--image", "missing.png"], ["P", "--width", "10"]):
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(flags)
                self.assertEqual(error.exception.code, 2)
        with patch("sys.stdin", io.StringIO("a" * 200 + "\nmore")), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main([])


@unittest.skipUnless(HAS_EXTRAS, "Install requirements.txt to test graphics and Persian")
class MediaTests(unittest.TestCase):
    def test_persian_joining_and_bitmap(self):
        from parnia_media import shape_persian
        shaped = shape_persian("پرنیا")
        self.assertNotEqual(shaped, "پرنیا"[::-1])
        self.assertTrue(any("\ufb50" <= c <= "\ufeff" for c in shaped))
        joined = render_text("پرنیا")
        separate = render_text("پ ر ن ی ا")
        self.assertIn("#", joined)
        self.assertNotEqual(joined, separate)
        self.assertIn("#", render_text("Parnia", style="rounded"))
        with self.assertRaises(ValueError):
            render_text("پرنیا", style="tiny")
        with self.assertRaises(ValueError):
            render_text("Parnia", style="rounded", font_path="missing-font.ttf")

    def test_image_brightness_and_alpha(self):
        from PIL import Image
        from parnia_media import image_to_ascii
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.png"
            image = Image.new("RGB", (20, 10), "white")
            for x in range(10):
                for y in range(10):
                    image.putpixel((x, y), (0, 0, 0))
            image.save(path)
            art = image_to_ascii(path, 20)
            self.assertEqual(len(art.splitlines()), 5)
            self.assertTrue(all(row.startswith("@@@@") for row in art.splitlines()))
            inverse = image_to_ascii(path, 20, invert=True)
            self.assertTrue(all(row.startswith("    ") for row in inverse.splitlines()))
            Image.new("RGBA", (20, 10), (0, 0, 0, 0)).save(path)
            self.assertNotIn("@", image_to_ascii(path, 20))
            with self.assertRaises(ValueError):
                image_to_ascii(path, 500)
            with self.assertRaises(ValueError):
                image_to_ascii(Path(folder) / "missing.png")

    def test_exports_and_gif_final_frame(self):
        from PIL import Image, ImageChops
        from parnia_media import export_art
        art = render_text("Parnia", theme="hearts")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            export_art(art, root / "art.txt")
            self.assertEqual((root / "art.txt").read_text(encoding="utf-8"), art + "\n")
            for palette in ("rainbow", "gradient", "neon"):
                png = root / f"{palette}.png"
                export_art(art, png, palette)
                with Image.open(png) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertGreater(len(image.getcolors(image.width * image.height)), 1)
            for effect in ("typewriter", "pixels", "fall"):
                gif = root / f"{effect}.gif"
                export_art(art, gif, "gradient", effect)
                with Image.open(gif) as image, Image.open(root / "gradient.png") as still:
                    self.assertGreater(image.n_frames, 1)
                    self.assertEqual(image.info["loop"], 0)
                    image.seek(image.n_frames - 1)
                    diff = ImageChops.difference(image.convert("RGB"), still.convert("RGB"))
                    # GIF palette quantization may change channel values slightly.
                    self.assertLess(max(diff.getextrema()[c][1] for c in range(3)), 32)
            with self.assertRaises(ValueError):
                export_art(art, root / "art.txt")
            with self.assertRaises(ValueError):
                export_art(art, root / "art.jpg")
            with self.assertRaises(ValueError):
                export_art(art, root / "bad.gif", delay=float("nan"))
            export_art("new", root / "art.txt", overwrite=True)

    def test_cli_export(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "demo.png"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["Parnia", "--theme", "binary", "--color", "neon",
                                       "--export", str(target)]), 0)
            self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
