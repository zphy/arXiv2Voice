#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for Paper2Voice text handling.

Run with: python -m pytest test_paper2voice.py -v
"""

import os
import tempfile

import pytest

from Paper2Voice import (
    ensure_utf8_inputenc,
    read_tex,
    strip_tables,
    write_tex,
)

# A line exercising the characters that arXiv sources actually contain and
# that the old cp437 read path destroyed: en-dash, umlaut, acute accents,
# multiplication sign and superscripts.
UNICODE_LINE = (
    "The Calderbank–Shor–Steane code, by György P. Gehér "
    "and Tamás Noszko, costs 5×10⁻³."
)


@pytest.fixture
def tmp_tex():
    fd, path = tempfile.mkstemp(suffix=".tex")
    os.close(fd)
    yield path
    if os.path.isfile(path):
        os.remove(path)


def test_reads_utf8_source_without_corruption(tmp_tex):
    """A UTF-8 .tex must come back as the same characters, not mojibake."""
    with open(tmp_tex, "w", encoding="utf-8") as f:
        f.write(UNICODE_LINE)

    assert read_tex(tmp_tex) == UNICODE_LINE


def test_round_trip_preserves_bytes(tmp_tex):
    """read_tex -> write_tex must be byte-identical for UTF-8 input.

    This is the actual failure mode: Paper2Voice reads the .tex, rewrites it,
    and hands it to latex2rtf. A lossy round trip is what produced spoken
    gibberish in the audio.
    """
    with open(tmp_tex, "w", encoding="utf-8") as f:
        f.write(UNICODE_LINE)
    original = open(tmp_tex, "rb").read()

    write_tex(tmp_tex, read_tex(tmp_tex))

    assert open(tmp_tex, "rb").read() == original


def test_falls_back_on_non_utf8_source(tmp_tex):
    """Older arXiv sources are latin-1; these must still read, not raise."""
    with open(tmp_tex, "wb") as f:
        f.write("Schön and Müller".encode("latin-1"))

    text = read_tex(tmp_tex)

    assert "Sch" in text and "n and M" in text
    assert "�" not in text  # no replacement chars


def test_write_tex_is_utf8_encoded(tmp_tex):
    """Output must be UTF-8 so latex2rtf and `say` receive valid text."""
    write_tex(tmp_tex, UNICODE_LINE)

    assert open(tmp_tex, "rb").read().decode("utf-8") == UNICODE_LINE


# latex2rtf 2.3.17 decides how to decode the source purely from the inputenc
# declaration -- the -C command-line codepage does not affect it. A paper that
# declares no inputenc (common for REVTeX sources, e.g. arXiv:2606.19482) is
# therefore read as latin-1, splitting each UTF-8 character into junk glyphs.
# Since write_tex always emits UTF-8, the preamble must say so.

def test_adds_inputenc_when_absent():
    src = "\\documentclass{article}\n\\begin{document}\nhi\n\\end{document}\n"

    out = ensure_utf8_inputenc(src)

    assert out.count("\\usepackage[utf8]{inputenc}") == 1
    assert out.index("\\usepackage[utf8]{inputenc}") < out.index("\\begin{document}")


def test_rewrites_non_utf8_inputenc():
    """A latin-1 source is re-encoded to UTF-8, so its declaration must follow."""
    src = ("\\documentclass{article}\n\\usepackage[latin1]{inputenc}\n"
           "\\begin{document}\nhi\n\\end{document}\n")

    out = ensure_utf8_inputenc(src)

    assert "latin1" not in out
    assert out.count("\\usepackage[utf8]{inputenc}") == 1


def test_leaves_existing_utf8_inputenc_alone():
    src = ("\\documentclass{article}\n\\usepackage[utf8]{inputenc}\n"
           "\\begin{document}\nhi\n\\end{document}\n")

    out = ensure_utf8_inputenc(src)

    assert out.count("\\usepackage[utf8]{inputenc}") == 1


def test_handles_multiline_documentclass_options():
    """REVTeX sources open with `\\documentclass[%` and options across lines."""
    src = ("\\documentclass[%\n aps,\n prl,\n]{revtex4-2}\n"
           "\\begin{document}\nhi\n\\end{document}\n")

    out = ensure_utf8_inputenc(src)

    assert out.count("\\usepackage[utf8]{inputenc}") == 1
    assert out.index("\\usepackage[utf8]{inputenc}") < out.index("\\begin{document}")
    assert "revtex4-2" in out


# Table floats are not stripped the way figures are, so their tabular bodies
# reach `say` and get read aloud as pipes, coordinates and colour-macro names
# ("myblue1", "9=4 myorange3"). In arXiv:2506.18061 the six table floats span
# 42k characters -- 56% of the extracted text, ~27 min of spoken markup.

TABLE_BODY = (
    "\\begin{tabular}{|c|c|}\n\\hline\n"
    "5=2 myblue1 & 9=4 myorange3 \\\\\n120 & 240 \\\\\n"
    "\\hline\n\\end{tabular}\n"
)


def test_replaces_table_with_its_caption():
    src = ("Before. \\begin{table}\n" + TABLE_BODY +
           "\\caption{Total ancilla size for each code family.}\n"
           "\\end{table}\n After.")

    out = strip_tables(src)

    assert "Total ancilla size for each code family." in out
    assert "myblue1" not in out
    assert "tabular" not in out
    assert "Before." in out and "After." in out


def test_handles_starred_table_environment():
    src = "\\begin{table*}\n" + TABLE_BODY + "\\caption{Wide table.}\n\\end{table*}\n"

    out = strip_tables(src)

    assert "Wide table." in out
    assert "myblue1" not in out


def test_drops_table_without_caption_entirely():
    src = "Before. \\begin{table}\n" + TABLE_BODY + "\\end{table}\n After."

    out = strip_tables(src)

    assert "myblue1" not in out
    assert "Before." in out and "After." in out


def test_caption_with_nested_braces_is_kept_whole():
    """Naive regex to the first '}' truncates captions containing math."""
    src = ("\\begin{table}\n" + TABLE_BODY +
           "\\caption{Overhead of $\\{a,b\\}$ codes at distance $d$.}\n\\end{table}")

    out = strip_tables(src)

    assert "codes at distance" in out
    assert "$d$." in out


def test_optional_short_caption_uses_long_form():
    src = ("\\begin{table}\n" + TABLE_BODY +
           "\\caption[short]{The long descriptive caption.}\n\\end{table}")

    out = strip_tables(src)

    assert "The long descriptive caption." in out
    assert "short" not in out


def test_multiple_tables_all_stripped():
    src = ("\\begin{table}\n" + TABLE_BODY + "\\caption{First.}\n\\end{table}\n"
           "Middle prose.\n"
           "\\begin{table*}\n" + TABLE_BODY + "\\caption{Second.}\n\\end{table*}")

    out = strip_tables(src)

    assert "First." in out and "Second." in out
    assert "Middle prose." in out
    assert out.count("myblue1") == 0
