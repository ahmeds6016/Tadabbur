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

    # Downgrade-not-drop: the wording is genuine Ibn Kathir content (Ahmad's
    # version), so the item survives — but the unverifiable "Sahih Muslim"
    # label must be stripped and surfaced only via the private downgrade key.
    assert dropped == []
    assert len(kept) == 1
    assert kept[0]["collection"] == ""
    assert kept[0]["_downgraded_collection"] == "Sahih Muslim"
    assert "Muslim" not in kept[0]["reference"]
    assert kept[0]["text"] == AHMAD_WORDING


def test_wholly_unsupported_collection_is_downgraded_not_shown():
    text = "Whoever recites this verse after every prayer will be under protection."
    context = f"One of the transmitted reports states: {text} Scholars mention its virtue."
    item = {
        "reference": {
            "collection": "Sahih al-Bukhari",
            "narrator": "Someone",
            "attribution": "As cited in Ibn Kathir's tafsir",
        },
        "text": text,
        "relevance": "Virtue of recitation.",
    }

    kept, dropped = validate_hadith_items([item], context)

    assert dropped == []
    assert len(kept) == 1
    assert kept[0]["collection"] == ""
    assert "Bukhari" not in kept[0]["reference"]


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


# --- Hyphenated collection names (models write "Sahih al-Bukhari") ---------------

import pytest
from services.hadith_validation import _infer_collection


@pytest.mark.parametrize("reference, expected", [
    ("Sahih al-Bukhari 6407", "Sahih al-Bukhari"),
    ("Riyad al-Saliheen 1234", "Riyad al-Salihin"),
    ("Riyad as-Salihin", "Riyad al-Salihin"),
    ("Sunan al-Nasa'i", "Sunan al-Nasa'i"),
    ("Sunan Abu Dawud", "Sunan Abi Dawud"),
    ("Sunan at-Tirmidhi", "Jami al-Tirmidhi"),
    ("Ibn Kathir's tafsir", ""),
    ("Ahmadiyya", ""),
])
def test_collection_names_are_recognised_with_hyphens_and_variants(reference, expected):
    assert _infer_collection(reference) == expected


def test_supported_hyphenated_collection_is_now_kept():
    text = "The best of you are those who learn the Quran and teach it to others."
    context = f"Sahih al-Bukhari records from Uthman: {text} This is the virtue of teaching."
    kept, dropped = validate_hadith_items(
        [{"reference": "Sahih al-Bukhari 5027", "text": text}], context)
    assert dropped == []
    assert kept[0]["collection"] == "Sahih al-Bukhari"
    assert "_downgraded_collection" not in kept[0]


def test_unsupported_hyphenated_collection_is_still_stripped():
    text = "The best of you are those who learn the Quran and teach it to others."
    context = f"Ibn Kathir mentions: {text} This is the virtue of teaching."
    kept, dropped = validate_hadith_items(
        [{"reference": "Sahih al-Bukhari 5027", "text": text}], context)
    assert dropped == []
    assert kept[0]["collection"] == ""
    assert kept[0]["_downgraded_collection"] == "Sahih al-Bukhari"
    assert "Bukhari" not in kept[0]["reference"]
