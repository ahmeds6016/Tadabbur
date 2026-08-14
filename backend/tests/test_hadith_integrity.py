"""Offline golden tests for source-grounded hadith validation."""

import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.hadith_validation import validate_hadith_items


AHMAD_WORDING = (
    "By Him in Whose Hand is my soul, this verse has a tongue and two lips "
    "with which it praises the King beside the leg of the Throne."
)


def test_composite_ayat_al_kursi_wording_is_not_attributed_to_muslim():
    context = (
        "Imam Ahmad recorded the following wording from Ubayy ibn Kab: "
        f"{AHMAD_WORDING} "
        "Muslim also collected the report, but did not include this additional wording."
    )
    item = {
        "reference": {
            "collection": "Sahih Muslim",
            "narrator": "Ubayy ibn Kab",
            "attribution": "As cited in Ibn Kathir's tafsir of 2:255",
        },
        "text": AHMAD_WORDING,
        "relevance": "It describes the virtue of Ayat al-Kursi.",
    }

    kept, dropped = validate_hadith_items([item], context)

    assert kept == []
    assert len(dropped) == 1
    assert dropped[0]["_validation_reason"] == "collection_not_attributed_to_wording"


def test_legitimate_verbatim_item_is_kept_with_display_reference():
    text = (
        "The strong believer is better and more beloved to Allah than the weak believer "
        "while there is good in both of them."
    )
    context = f"Sahih Muslim records from Abu Hurayrah: {text} Continue with what benefits you."
    item = {
        "reference": {
            "collection": "Sahih Muslim",
            "narrator": "Abu Hurayrah",
            "attribution": "As cited in Riyad al-Saliheen",
        },
        "text": text,
        "relevance": "A source-grounded application.",
    }

    kept, dropped = validate_hadith_items([item], context)

    assert dropped == []
    assert len(kept) == 1
    assert kept[0]["reference"] == (
        "Sahih Muslim; narrated by Abu Hurayrah; As cited in Riyad al-Saliheen"
    )
    assert kept[0]["collection"] == "Sahih Muslim"
    assert kept[0]["text"] == text
    assert kept[0]["relevance"] == "A source-grounded application."


def test_item_absent_from_source_context_is_dropped():
    item = {
        "reference": {
            "collection": None,
            "narrator": "A narrator",
            "attribution": "As cited in Ibn Kathir's tafsir",
        },
        "text": (
            "This invented report is wholly absent from every excerpt that the model "
            "received for this particular verse and response."
        ),
        "relevance": "It should never be shown.",
    }

    kept, dropped = validate_hadith_items([item], "The supplied context discusses a different subject entirely.")

    assert kept == []
    assert len(dropped) == 1
    assert dropped[0]["_validation_reason"].startswith("source_text_match=")


def test_empty_hadith_list_is_valid():
    assert validate_hadith_items([], "Any source context") == ([], [])
    assert validate_hadith_items(None, "Any source context") == ([], [])
