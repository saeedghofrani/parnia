import subprocess
import sys
import unittest
from pathlib import Path

from parnia import render


class ArtTests(unittest.TestCase):
    def test_known_letter(self):
        self.assertEqual(render("P", "."), "....\n.   .\n.   .\n....\n.\n.\n.")

    def test_case_and_spaces(self):
        self.assertEqual(render("Parnia"), render("PARNIA"))
        self.assertGreater(len(render("A B").splitlines()[0]),
                           len(render("AB").splitlines()[0]))

    def test_scale_and_multiline(self):
        self.assertEqual(len(render("A", scale=2).splitlines()), 14)
        self.assertEqual(render("A\nB"), render("A") + "\n\n" + render("B"))

    def test_invalid_input(self):
        for text, character, scale in [("", "#", 1), ("hello ♥", "#", 1),
                                       ("A", "xx", 1), ("A", "\x1b", 1),
                                       ("A", " ", 1), ("A", "#", 0),
                                       ("A" * 201, "#", 1)]:
            with self.subTest(text=text, character=character, scale=scale):
                with self.assertRaises(ValueError):
                    render(text, character, scale)

    def test_cli_and_stdin(self):
        script = str(Path(__file__).resolve().parents[1] / "parnia.py")
        direct = subprocess.run([sys.executable, script, "Parnia", "--char", "1"],
                                capture_output=True, text=True)
        self.assertEqual(direct.returncode, 0)
        self.assertEqual(direct.stdout.rstrip(), render("Parnia", "1"))
        piped = subprocess.run([sys.executable, script], input="Parnia\n",
                               capture_output=True, text=True)
        self.assertEqual(piped.returncode, 0)
        self.assertEqual(piped.stdout.rstrip(), render("Parnia\n").rstrip())
        invalid = subprocess.run([sys.executable, script, "♥"],
                                 capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("Unsupported characters", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
