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
    strip_bibliography,
    strip_references_heading,
    strip_tables,
    unwrap_widetext,
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


# REVTeX wraps wide content -- often the entire supplementary section -- in
# \begin{widetext}. latex2rtf 2.3.17 does not support it and discards the whole
# block ("Sorry. Ignored \begin{widetext} ... \end{widetext}"). For
# arXiv:2506.18061 that silently dropped 49k characters of appendix prose from
# --si output, more than the rest of the paper combined. The environment is
# purely a layout directive, so unwrapping it loses nothing.

def test_unwraps_widetext_keeping_content():
    src = ("Before. \\begin{widetext}\n\\section{Formal definitions}\n"
           "The code is a stabilizer code.\n\\end{widetext}\n After.")

    out = unwrap_widetext(src)

    assert "widetext" not in out
    assert "Formal definitions" in out
    assert "The code is a stabilizer code." in out
    assert "Before." in out and "After." in out


def test_unwraps_every_widetext_block():
    src = ("\\begin{widetext}\nFirst body.\n\\end{widetext}\n mid \n"
           "\\begin{widetext}\nSecond body.\n\\end{widetext}")

    out = unwrap_widetext(src)

    assert "widetext" not in out
    assert "First body." in out and "Second body." in out and "mid" in out


def test_widetext_star_variant_also_unwrapped():
    src = "\\begin{widetext*}\nBody text.\n\\end{widetext*}"

    out = unwrap_widetext(src)

    assert "widetext" not in out
    assert "Body text." in out


# strip_bibliography extracts the bibliography-removal regexes that used to
# live inline in main() -- pulled out so the always-on "never read citations"
# behavior is directly testable instead of only exercised end-to-end.

def test_strip_bibliography_removes_thebibliography_environment():
    src = ("Body text.\n\\begin{thebibliography}{99}\n"
           "\\bibitem{a} Author, Title, Journal (2020).\n"
           "\\end{thebibliography}\n\\end{document}")

    out = strip_bibliography(src)

    assert "thebibliography" not in out
    assert "Author, Title, Journal" not in out
    assert "Body text." in out


def test_strip_bibliography_removes_bibliography_command():
    src = "Body text.\n\\bibliography{refs}\n\\end{document}"

    out = strip_bibliography(src)

    assert "\\bibliography" not in out
    assert "Body text." in out


def test_strip_bibliography_removes_biblatex_commands():
    src = ("Body text.\n\\addbibresource{refs.bib}\n"
           "\\printbibliography\n\\bibliographystyle{plain}\n\\end{document}")

    out = strip_bibliography(src)

    assert "addbibresource" not in out
    assert "printbibliography" not in out
    assert "bibliographystyle" not in out


# strip_references_heading is the new fallback for papers that never run
# BibTeX at all -- the reference list is just prose typed under a
# \section{References} heading, which strip_bibliography has no way to catch
# since there is no \bibliography command or thebibliography environment.
# arXiv:2603.18318 shows the environment case is already handled correctly
# (the thebibliography block sits inside \appendix and strip_bibliography
# removes it in place, leaving the real appendix prose intact) -- this
# function is strictly for papers with no BibTeX machinery at all.

def test_strip_references_heading_removes_manual_reference_list():
    src = ("Main text.\n\\section{References}\n"
           "[1] Author, Title, Journal (2020).\n"
           "[2] Other, Paper, Conf (2021).\n"
           "\\end{document}")

    out = strip_references_heading(src)

    assert "References" not in out
    assert "Author, Title, Journal" not in out
    assert "Main text." in out


def test_strip_references_heading_is_case_insensitive_and_handles_starred_section():
    src = "Main text.\n\\section*{Bibliography}\n[1] Someone (2019).\n\\end{document}"

    out = strip_references_heading(src)

    assert "Someone" not in out
    assert "Main text." in out


def test_strip_references_heading_stops_at_next_section():
    """A references list followed by more body sections must not eat them."""
    src = ("Main text.\n\\section{References}\n[1] Someone (2019).\n"
           "\\section{Acknowledgments}\nThanks to everyone.\n\\end{document}")

    out = strip_references_heading(src)

    assert "Someone" not in out
    assert "Acknowledgments" in out and "Thanks to everyone." in out


def test_strip_references_heading_preserves_appendix_that_follows():
    """The real motivating case: refs before appendix must not eat the supplement."""
    src = ("Main text.\n\\section{References}\n[1] Someone (2019).\n"
           "\\appendix\n\\section{Extra derivation}\nDetailed proof here.\n"
           "\\end{document}")

    out = strip_references_heading(src)

    assert "Someone" not in out
    assert "Extra derivation" in out and "Detailed proof here." in out


def test_strip_references_heading_no_op_when_absent():
    src = "Main text.\n\\section{Conclusion}\nWe are done.\n\\end{document}"

    out = strip_references_heading(src)

    assert out == src
