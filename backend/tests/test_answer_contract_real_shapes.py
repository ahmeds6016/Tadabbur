"""The answer contract must accept answers exactly as Gemini and post-processing shape them.

Fixtures are trimmed from a real gemini-3.8-flash answer for 2:255 (2026-10-17 canary).
Post-processing stores `surah` as an int while the model writes it as a name; a contract
that accepted only strings rejected every cached answer, so nothing was ever served from
cache and shares could not be created.
"""

import ast
import copy
from pathlib import Path

import pytest


def _load():
    path = Path(__file__).resolve().parents[1] / "app.py"
    node = next(n for n in ast.parse(path.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == "valid_answer_contract")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["valid_answer_contract"]


valid_answer_contract = _load()

STORED_ANSWER = {
    "verses": [{
        "arabic_text": "ٱللَّهُ لَآ إِلَـٰهَ إِلَّا هُوَ ٱلْحَىُّ ٱلْقَيُّومُ",
        "surah": 2,
        "surah_name": "Al-Baqarah",
        "text_saheeh_international": "Allah - there is no deity except Him, the Ever-Living, the Sustainer.",
        "verse_number": "255",
    }],
    "tafsir_explanations": [
        {"source": "al-Qurtubi", "explanation": "**The Core Meaning**\n\nThis verse declares..."},
        {"source": "Ibn Kathir", "explanation": "**The Foundation of Devotion**\n\nThis verse conveys..."},
    ],
    "cross_references": [{"verse": "20:111", "relevance": "Echoes how all faces submit."}],
    "hadith": [{
        "attribution": "As cited in Ibn Kathir's tafsir of this verse",
        "collection": "Imam Ahmad",
        "narrator": "Ubayy bin Ka'b",
        "reference": "Imam Ahmad; narrated by Ubayy bin Ka'b; As cited in Ibn Kathir's tafsir of this verse",
        "relevance": "Identifies Ayat al-Kursi as the greatest verse.",
        "text": "the Prophet asked him about the greatest Ayah in the Book of Allah",
    }],
    "lessons_practical_applications": [
        {"point": "The Quiet Comfort of an Untiring Sustainer", "type": "synthesis", "body": "When a community..."},
        {"point": "Awakening to Continuous Presence", "type": "contemplation",
         "core_principle": "True peace comes from...", "contemplation": "If the Sustainer...",
         "prophetic_anchor": "Classical scholars highlight..."},
    ],
    "summary": "Known as Ayat al-Kursi, this verse represents the central jewel of the Quran.",
    "reflection_prompt": "When you consider your own daily fatigue, what worry can you let go of?",
}


def test_stored_answer_with_numeric_surah_is_valid():
    assert valid_answer_contract(STORED_ANSWER)


def test_model_output_with_surah_name_is_valid():
    answer = copy.deepcopy(STORED_ANSWER)
    answer["verses"][0]["surah"] = "Al-Baqarah"
    answer["verses"][0]["verse_number"] = 255
    assert valid_answer_contract(answer)


def test_answer_with_no_hadith_is_valid():
    answer = copy.deepcopy(STORED_ANSWER)
    answer["hadith"] = []
    assert valid_answer_contract(answer)


@pytest.mark.parametrize("mutate", [
    lambda a: a["verses"][0].__setitem__("surah", None),
    lambda a: a["verses"][0].__setitem__("surah", 2.0),
    lambda a: a["verses"][0].pop("text_saheeh_international"),
    lambda a: a.__setitem__("tafsir_explanations", []),
    lambda a: a["tafsir_explanations"].__setitem__(slice(None), [{"source": " ", "explanation": " "}]),
    lambda a: a.__setitem__("summary", ""),
    lambda a: a.__setitem__("metadata", {"extraction_error": "fallback"}),
])
def test_incomplete_or_malformed_answers_still_fail(mutate):
    answer = copy.deepcopy(STORED_ANSWER)
    mutate(answer)
    assert not valid_answer_contract(answer)
