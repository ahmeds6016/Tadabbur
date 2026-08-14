"""Pure persona learning-contract prompt blocks."""


PERSONA_CONTRACTS = {
    "new_revert": (
        "Start with the plain meaning before introducing background. Explain every "
        "Arabic term on first use in simple language. Give exactly one concrete action "
        "across the lessons, and do not add extra action steps. Present a unified "
        "explanation without scholarly debate."
    ),
    "curious_explorer": (
        "Use a context-first narrative that shows why the verse speaks here. Weave one "
        "open question into that narrative to invite exploration without assuming belief "
        "or prior knowledge."
    ),
    "practicing_muslim": (
        "Emphasize worship and character application in the lessons. Connect the verse "
        "to sincere practice, habits of the heart, and conduct toward other people."
    ),
    "student": (
        "Name and compare scholarly positions with source locators: use formulations such "
        "as 'Ibn Kathir states in his tafsir of this verse...' and 'al-Qurtubi holds in his "
        "tafsir of this verse...'. Encourage comparison, preserve distinctions, and never "
        "invent a locator absent from the supplied material."
    ),
    "advanced_learner": (
        "Analyze Arabic rhetoric when it is grounded in the supplied sources. Present "
        "scholarly disagreements, assess evidence strength, and state uncertainty "
        "explicitly where the sources differ or do not settle a point."
    ),
}


def _verse_reference(verse_data):
    """Return a compact reference for prompt context without external dependencies."""
    if isinstance(verse_data, list) and verse_data:
        first = verse_data[0]
        last = verse_data[-1]
        surah = first.get("surah_number", first.get("surah", "?"))
        start = first.get("verse_number", first.get("verse", "?"))
        end = last.get("verse_number", last.get("verse", start))
        return f"{surah}:{start}" if start == end else f"{surah}:{start}-{end}"
    if isinstance(verse_data, dict):
        surah = verse_data.get("surah_number", verse_data.get("surah", "?"))
        verse = verse_data.get("verse_number", verse_data.get("verse", "?"))
        return f"{surah}:{verse}"
    return "the requested verse"


def build_persona_learning_contract(persona_name, verse_data=None):
    """Build the persona-specific and universal learning directives for a prompt."""
    contract = PERSONA_CONTRACTS.get(persona_name, PERSONA_CONTRACTS["practicing_muslim"])
    return f"""Verse under study: {_verse_reference(verse_data)}

PERSONA-SPECIFIC CONTRACT:
{contract}

UNIVERSAL MEANING-FIRST CONTRACT:
The first two sentences of EACH tafsir_explanations[].explanation must directly answer
'What does this verse mean here?' before adding scholarly context or application.

UNIVERSAL REFLECTION CONTRACT:
Build reflection_prompt from a tension, image, contrast, or command specific to this
verse. Name that concrete anchor in the question; never substitute a generic prompt."""
