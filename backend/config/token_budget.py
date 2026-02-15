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
# Each verse in the response requires Gemini to produce a structured JSON
# response including tafsir explanations, cross-references, hadith, and
# lessons.  This allocation ensures we don't overload Gemini with too many
# verses — keeping input small enough that output stays within 65K limit.
OUTPUT_TOKENS_PER_VERSE = 2_000

# ---------------------------------------------------------------------------
# Derived budget for verses + tafsir context
# ---------------------------------------------------------------------------
# Output is allocated PER-VERSE (not as a global flat reserve), so we only
# subtract fixed per-query costs here.  Per-verse output allocation is added
# to each verse's cost in precompute_verse_budgets().
VERSE_AND_TAFSIR_BUDGET = (
    PRACTICAL_INPUT_BUDGET
    - PROMPT_OVERHEAD_TOKENS
    - SCHOLARLY_RESERVE_TOKENS
)  # = 22 000 tokens

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
ABSOLUTE_MAX_VERSES = 5              # Matches real-world output capacity
ABSOLUTE_MIN_VERSES = 1              # Always allow at least 1 verse
