#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for Paper2Voice text handling.

Run with: python -m pytest test_paper2voice.py -v
"""

import os
import tempfile

import pytest

from Paper2Voice import read_tex, write_tex

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
