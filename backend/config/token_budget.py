"""
Token budget configuration for the dropdown guardrail system.

All token budget constants live here. Import from this module only.
Keeps budgeting tunable from a single source — no hardcoding elsewhere.
"""

# ---------------------------------------------------------------------------
# Model limits
# ---------------------------------------------------------------------------
MODEL_MAX_INPUT_TOKENS = 1_000_000       # Gemini 2.5 Flash input limit
MODEL_MAX_OUTPUT_TOKENS = 65_536         # Gemini 2.5 Flash output limit

# Practical budget — existing truncation target (cost/latency, not model cap)
PRACTICAL_INPUT_BUDGET = 50_000

# ---------------------------------------------------------------------------
# Token estimation ratios (characters per token)
# ---------------------------------------------------------------------------
CHARS_PER_TOKEN_AR = 2    # Arabic script: ~2 chars per token
CHARS_PER_TOKEN_EN = 4    # English / transliteration: ~4 chars per token
CHARS_PER_TOKEN_MIXED = 3 # Mixed content default

# ---------------------------------------------------------------------------
# Budget reservations (in tokens)
# ---------------------------------------------------------------------------
PROMPT_OVERHEAD_TOKENS = 4_000       # Static prompt template (persona, instructions, JSON schema)
OUTPUT_RESERVE_TOKENS = 16_384       # Reserved for model output
SCHOLARLY_RESERVE_TOKENS = 3_500     # MAX_TOTAL_SCHOLARLY_CHARS (12 000) / ~3.4 chars/tok
RAG_OVERHEAD_TOKENS = 500            # Cross-refs, Arabic text block, section headers

# ---------------------------------------------------------------------------
# Derived budget for verses + tafsir context
# ---------------------------------------------------------------------------
VERSE_AND_TAFSIR_BUDGET = (
    PRACTICAL_INPUT_BUDGET
    - PROMPT_OVERHEAD_TOKENS
    - OUTPUT_RESERVE_TOKENS
    - SCHOLARLY_RESERVE_TOKENS
    - RAG_OVERHEAD_TOKENS
)  # = 25 616 tokens

# ---------------------------------------------------------------------------
# Fixed per-verse allowance for verse text (Arabic + English + transliteration)
# ---------------------------------------------------------------------------
# Verse text is NOT in memory at startup (it's fetched from Firestore per-query).
# This is a fixed allowance — not an estimate of tafsir size.  Verse text is
# small and predictable: Arabic (~50-100 tok) + English (~40-80) + transliteration
# (~30-70).  Even the longest verse (2:282) fits in ~250 tokens.
VERSE_TEXT_TOKENS_PER_VERSE = 250

# ---------------------------------------------------------------------------
# Safety margin
# ---------------------------------------------------------------------------
SAFETY_FACTOR = 0.90    # 10% safety margin

# ---------------------------------------------------------------------------
# Hard limits
# ---------------------------------------------------------------------------
ABSOLUTE_MAX_VERSES = 10             # Never exceed regardless of budget
ABSOLUTE_MIN_VERSES = 1              # Always allow at least 1 verse
