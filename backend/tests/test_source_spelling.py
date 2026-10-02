"""Cached answers written before the spelling change must render the house spelling."""

import ast
from pathlib import Path
import re


def _load():
    path = Path(__file__).resolve().parents[1] / "app.py"
    wanted = {"_RIYAD_SPELLING", "_house_spelling", "normalize_source_spellings"}
    body = []
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            body.append(node)
        elif isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) in wanted for t in node.targets):
            body.append(node)
    namespace = {"re": re}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["normalize_source_spellings"]


normalize = _load()


def test_cached_answer_is_rewritten_in_place_everywhere():
    answer = {
        "hadith": [{"attribution": "As cited in Riyad al-Saliheen", "reference": "riyad as-salihin 12"}],
        "tafsir_explanations": [{"explanation": "In Riyad al-Saliheen, al-Nawawi records this."}],
        "summary": "Unrelated text stays exactly the same.",
        "verses": [{"arabic_text": "ٱلَّذِينَ ءَامَنُوا۟", "verse_number": 28}],
    }
    same_object = answer
    normalize(answer)
    assert answer is same_object
    assert answer["hadith"][0]["attribution"] == "As cited in Riyad al-Salihin"
    assert answer["hadith"][0]["reference"] == "Riyad al-Salihin 12"
    assert answer["tafsir_explanations"][0]["explanation"] == "In Riyad al-Salihin, al-Nawawi records this."
    assert answer["summary"] == "Unrelated text stays exactly the same."
    assert answer["verses"][0] == {"arabic_text": "ٱلَّذِينَ ءَامَنُوا۟", "verse_number": 28}


def test_already_correct_spelling_is_idempotent():
    answer = {"note": "Riyad al-Salihin"}
    normalize(answer)
    normalize(answer)
    assert answer == {"note": "Riyad al-Salihin"}
