"""Recommendation reasons must never be cut mid-word."""

import ast
from pathlib import Path


def _load(name):
    path = Path(__file__).resolve().parents[1] / "app.py"
    node = next(n for n in ast.parse(path.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


shorten = _load("_shorten_on_word")
LONG = ("Highlights how thoughtful reflection on divine truth distinguishes "
        "those who truly understand the signs of God")


def test_long_reason_ends_on_a_whole_word_with_ellipsis():
    result = shorten(LONG, 80)
    assert len(result) <= 80
    assert result.endswith("…")
    assert LONG.startswith(result[:-1])
    assert LONG[len(result) - 1] == " "


def test_text_within_limit_is_unchanged():
    exact = "Emphasizes that signs and reminders benefit those whose hearts are open to faith"
    assert len(exact) == 80
    assert shorten(exact, 80) == exact
    assert shorten("Related verse", 80) == "Related verse"


def test_single_overlong_word_is_still_bounded():
    result = shorten("A" * 120, 80)
    assert len(result) == 80 and result.endswith("…")


def test_whitespace_is_normalised():
    assert shorten("  Related \n  verse  ", 80) == "Related verse"
