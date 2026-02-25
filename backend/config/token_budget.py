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

# ---------------------------------------------------------------------------
# Practical budget — REAL-WORLD limit from production experience
# ---------------------------------------------------------------------------
# Although Gemini accepts 1M input tokens, large inputs cause the OUTPUT
# to balloon beyond the 65K output limit.  From production testing, the
# safe input range is 25-30K tokens total.  We use 30K as the upper bound.
PRACTICAL_INPUT_BUDGET = 30_000

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
SCHOLARLY_RESERVE_TOKENS = 4_000     # MAX_TOTAL_SCHOLARLY_CHARS (14 000) / ~3.5 chars/tok

# ---------------------------------------------------------------------------
# Per-verse output allocation
# ---------------------------------------------------------------------------
# The PER-VERSE output cost covers only what scales with verse count:
# tafsir explanation per source (~500-1000 tokens) + verse JSON (~100 tokens).
# Shared sections (summary, lessons, hadith, reflection) are covered by
# FIXED_OUTPUT_RESERVE below.
OUTPUT_TOKENS_PER_VERSE = 1_000

# ---------------------------------------------------------------------------
# Fixed output reserve (shared sections that don't scale with verse count)
# ---------------------------------------------------------------------------
# Summary (~300), 3 lessons (~1500), hadith (~300), cross-refs (~200),
# reflection (~100) = ~2400 tokens.  Rounded up for safety.
FIXED_OUTPUT_RESERVE = 2_500

# ---------------------------------------------------------------------------
# Derived budget for verses + tafsir context
# ---------------------------------------------------------------------------
VERSE_AND_TAFSIR_BUDGET = (
    PRACTICAL_INPUT_BUDGET
    - PROMPT_OVERHEAD_TOKENS
    - SCHOLARLY_RESERVE_TOKENS
    - FIXED_OUTPUT_RESERVE
)  # = 19 500 tokens

# ---------------------------------------------------------------------------
# Fixed per-verse allowance for verse text (Arabic + English + transliteration)
# ---------------------------------------------------------------------------
VERSE_TEXT_TOKENS_PER_VERSE = 250

# ---------------------------------------------------------------------------
# Safety margin
# ---------------------------------------------------------------------------
SAFETY_FACTOR = 0.90    # 10% safety margin

# ---------------------------------------------------------------------------
# Hard limits
# ---------------------------------------------------------------------------
ABSOLUTE_MAX_VERSES = 10             # Upper bound; real limit is token budget
ABSOLUTE_MIN_VERSES = 1              # Always allow at least 1 verse
