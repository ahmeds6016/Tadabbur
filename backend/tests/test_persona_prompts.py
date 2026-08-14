"""Offline tests for mutually distinct persona learning contracts."""

import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.persona_prompt_service import build_persona_learning_contract


VERSE_2_255 = {
    "surah_number": 2,
    "surah_name": "Al-Baqarah",
    "verse_number": 255,
    "arabic": "Fixture Arabic text",
    "english": "Allah—there is no deity except Him, the Ever-Living, the Sustainer.",
    "transliteration": "Fixture transliteration",
}

DISTINGUISHING_INSTRUCTIONS = {
    "new_revert": "Explain every Arabic term on first use",
    "curious_explorer": "Use a context-first narrative",
    "practicing_muslim": "Emphasize worship and character application",
    "student": "Name and compare scholarly positions with source locators",
    "advanced_learner": "Analyze Arabic rhetoric",
}


def test_all_persona_prompts_share_meaning_first_and_specific_reflection_contracts():
    for persona_name in DISTINGUISHING_INSTRUCTIONS:
        prompt = build_persona_learning_contract(persona_name, VERSE_2_255)

        assert "Verse under study: 2:255" in prompt
        assert "The first two sentences of EACH tafsir_explanations[].explanation" in prompt
        assert "directly answer\n'What does this verse mean here?'" in prompt
        assert "Build reflection_prompt from a tension, image, contrast, or command" in prompt
        assert "never substitute a generic prompt" in prompt


def test_each_persona_prompt_contains_only_its_distinguishing_instruction():
    prompts = {
        persona_name: build_persona_learning_contract(persona_name, VERSE_2_255)
        for persona_name in DISTINGUISHING_INSTRUCTIONS
    }

    for persona_name, prompt in prompts.items():
        assert DISTINGUISHING_INSTRUCTIONS[persona_name] in prompt
        for other_name, other_instruction in DISTINGUISHING_INSTRUCTIONS.items():
            if other_name != persona_name:
                assert other_instruction not in prompt


def test_persona_contract_details_match_the_learning_goals():
    prompts = {
        persona_name: build_persona_learning_contract(persona_name, VERSE_2_255)
        for persona_name in DISTINGUISHING_INSTRUCTIONS
    }

    assert "exactly one concrete action" in prompts["new_revert"]
    assert "without scholarly debate" in prompts["new_revert"]
    assert "one open question" in prompts["curious_explorer"]
    assert "habits of the heart" in prompts["practicing_muslim"]
    assert "Ibn Kathir states in his tafsir of this verse" in prompts["student"]
    assert "al-Qurtubi holds in his tafsir of this verse" in prompts["student"]
    assert "assess evidence strength" in prompts["advanced_learner"]
    assert "state uncertainty explicitly" in prompts["advanced_learner"]
