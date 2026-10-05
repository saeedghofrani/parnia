# Parnia

Turn a name, word or short message into character art in your console.
A small Python art project with no external dependencies.

```text
####    ###   ####   #   #  #####   ###
#   #  #   #  #   #  ##  #    #    #   #
#   #  #   #  #   #  # # #    #    #   #
####   #####  ####   #  ##    #    #####
#      #   #  # #    #   #    #    #   #
#      #   #  #  #   #   #    #    #   #
#      #   #  #   #  #   #  #####  #   #
```

## Quick start

Requires **Python 3.10 or newer** on Windows, macOS or Linux.

```sh
git clone https://github.com/saeedghofrani/parnia.git
cd parnia
python parnia.py
```

On systems where Python is named `python3`, use `python3` instead.

Choose a drawing character (press Enter for `#`), then type `Parnia` or
another word at `Text >`. Keep entering text to make more art.
Type `/quit` or press Ctrl+C to exit.

## Command-line examples

```sh
python parnia.py Parnia
python parnia.py "Hello world" --char .
python parnia.py Parnia --char 1
python parnia.py Parnia --char _
python parnia.py Parnia --char=-
python parnia.py Parnia --char "*" --scale 2
python parnia.py --help
```

`#` is the default because its solid shape makes the letters easy to read.
`.` gives a dotted style; `1`, `_`, `-`, and other visible single-width
characters work too. Quote shell-special characters such as `*` or `#`.
Scale can be from 1 to 5.

You can pipe text into the app or save the result:

```sh
echo Parnia | python parnia.py --char .
python parnia.py Parnia > art.txt
```

## Supported text

- English letters A–Z (lowercase input is drawn as uppercase).
- Digits 0–9, spaces and punctuation: `. , ! ? - _ : / + '`.
- Multiple lines when using piped input or the Python API.
- Up to 200 characters per render, including spaces and newlines.

Unsupported characters produce a clear error. The built-in font does not
yet cover Persian or other scripts. Long output may wrap in narrow terminals;
use shorter words, scale 1, a wider terminal, or redirect to a file.
Use a monospaced font to keep the art aligned.

## Use from Python

```python
from parnia import render

print(render("Parnia", character=".", scale=1))
```

The font and renderer are in `parnia.py`; new glyphs can be added to
`_PATTERNS` as seven rows of five binary pixels (`1` filled, `0` empty).

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests cover recognizable glyph output, lowercase input, word spacing,
scaling, multiline rendering, invalid input, command-line use and piped text.

Created by [Saeed Ghofrani](https://github.com/saeedghofrani).
