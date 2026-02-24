"""
Comprehensive tests for backend/utils/text_cleaning.py

50 test cases covering sanitize_heading_format() and sanitize_explanation_text().
Tests simulate realistic Gemini LLM output patterns including malformed bold headings,
missing line breaks, mixed spacing, and edge cases.
"""
import sys
import os

# Add backend to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.text_cleaning import sanitize_heading_format

# Also import sanitize_explanation_text from app.py for pipeline tests
# We'll define a local copy since it's a standalone function
def sanitize_explanation_text(text):
    """Mirror of the function in app.py for testing the full pipeline."""
    if not text:
        return text
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.lstrip()
        leading_spaces = len(line) - len(stripped)
        if leading_spaces > 4:
            line = '    ' + stripped if stripped else ''
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)


def full_pipeline(text):
    """Simulate the real pipeline: sanitize_explanation_text -> sanitize_heading_format."""
    return sanitize_heading_format(sanitize_explanation_text(text))


PASS = 0
FAIL = 0
ERRORS = []


def check(test_num, description, input_text, expected_substring=None,
          must_not_contain=None, expected_exact=None, use_pipeline=False):
    """Run a single test case."""
    global PASS, FAIL, ERRORS

    try:
        if use_pipeline:
            result = full_pipeline(input_text)
        else:
            result = sanitize_heading_format(input_text)

        ok = True
        reasons = []

        if expected_exact is not None:
            if result != expected_exact:
                ok = False
                reasons.append(f"Expected exact match but got different result")

        if expected_substring is not None:
            if isinstance(expected_substring, str):
                expected_substring = [expected_substring]
            for sub in expected_substring:
                if sub not in result:
                    ok = False
                    reasons.append(f"Missing expected: {repr(sub)}")

        if must_not_contain is not None:
            if isinstance(must_not_contain, str):
                must_not_contain = [must_not_contain]
            for bad in must_not_contain:
                if bad in result:
                    ok = False
                    reasons.append(f"Should NOT contain: {repr(bad)}")

        if ok:
            PASS += 1
            print(f"  PASS #{test_num}: {description}")
        else:
            FAIL += 1
            detail = "; ".join(reasons)
            ERRORS.append((test_num, description, detail, input_text, result))
            print(f"  FAIL #{test_num}: {description} — {detail}")

    except Exception as e:
        FAIL += 1
        ERRORS.append((test_num, description, str(e), input_text, "EXCEPTION"))
        print(f"  FAIL #{test_num}: {description} — EXCEPTION: {e}")


def run_all_tests():
    print("=" * 70)
    print("TEXT CLEANING TESTS — 50 cases")
    print("=" * 70)

    # ─── SECTION A: Bold heading + text smashed together (core bug fix) ───

    print("\n--- A: Bold heading smashed against text (core bug) ---")

    check(1, "**Heading**Text with no space",
          '**The Throne Verse**This verse discusses...',
          expected_substring='**The Throne Verse**\n\n',
          must_not_contain='**The Throne Verse**This')

    check(2, "**Heading** followed by quoted text",
          '**Key Insight**"Allah says in the Quran..."',
          expected_substring='**Key Insight**\n\n"Allah',
          must_not_contain='**Key Insight**"')

    check(3, "**Heading** followed by digit",
          '**Verse Analysis**2:255 is known as...',
          expected_substring='**Verse Analysis**\n\n2:255',
          must_not_contain='**Verse Analysis**2')

    check(4, "**Heading** followed by parenthetical",
          '**Context**(See also 3:18) The scholars...',
          expected_substring='**Context**\n\n(See',
          must_not_contain='**Context**(')

    check(5, "**Heading** followed by single-quoted text",
          "**Linguistic Note**'Rabb' means Lord...",
          expected_substring="**Linguistic Note**\n\n'Rabb'",
          must_not_contain="**Linguistic Note**'")

    check(6, "**Heading** followed by backtick",
          '**Code Example**`verse_ref`...',
          expected_substring='**Code Example**\n\n`verse',
          must_not_contain='**Code Example**`')

    check(7, "**Heading** followed by bracket",
          '**References**[Ibn Kathir] noted...',
          expected_substring='**References**\n\n[Ibn',
          must_not_contain='**References**[')

    # ─── SECTION B: Text before heading (missing line break before) ───

    print("\n--- B: Missing line break BEFORE heading ---")

    check(8, "Period then heading",
          'This ends a sentence.**Next Section**The text continues.',
          expected_substring=['sentence.\n\n**Next Section**\n\n', 'The text continues.'])

    check(9, "Question mark then heading",
          'Is this correct?**Answer**Yes it is.',
          expected_substring='correct?\n\n**Answer**\n\nYes')

    check(10, "Exclamation then heading",
          'SubhanAllah!**Reflection**Consider this...',
          expected_substring='SubhanAllah!\n\n**Reflection**\n\nConsider')

    check(11, "Colon then heading",
          'The scholars said:**Opinion of Imam Malik**He believed...',
          expected_substring='said:\n\n**Opinion of Imam Malik**\n\nHe')

    check(12, "Close-paren then heading",
          'mentioned in (2:255)**Deeper Analysis**The verse...',
          expected_substring='(2:255)\n\n**Deeper Analysis**\n\nThe')

    check(13, "Close-quote then heading",
          'He said "Alhamdulillah"**Scholarly Commentary**Several...',
          expected_substring='"Alhamdulillah"\n\n**Scholarly Commentary**\n\nSeveral')

    # ─── SECTION C: Already properly formatted (should NOT double-break) ───

    print("\n--- C: Already correct formatting (no-ops) ---")

    check(14, "Heading already has \\n\\n after",
          '**Title**\n\nParagraph text here.',
          must_not_contain='\n\n\n')

    check(15, "Heading with \\n\\n before and after",
          'End of section.\n\n**New Section**\n\nStart of new.',
          must_not_contain='\n\n\n')

    check(16, "Multiple headings all properly separated",
          '**First**\n\nContent one.\n\n**Second**\n\nContent two.',
          must_not_contain='\n\n\n')

    # ─── SECTION D: Single newline upgrade to double ───

    print("\n--- D: Single \\n upgraded to \\n\\n ---")

    check(17, "Heading with single \\n after, then text",
          '**Heading**\nThe content starts here.',
          expected_substring='**Heading**\n\nThe content')

    check(18, "Period, single \\n, then heading",
          'End of paragraph.\n**New Topic**\nMore text.',
          expected_substring=['paragraph.\n\n**New Topic**\n\nMore text'])

    # ─── SECTION E: Space normalization inside ** ** ───

    print("\n--- E: Spaces inside ** markers ---")

    check(19, "** Heading ** with spaces",
          '** Historical Context **The Prophet said...',
          expected_substring='**Historical Context**\n\nThe')

    check(20, "**Heading ** trailing space",
          '**Key Point **This is important.',
          expected_substring='**Key Point**\n\nThis')

    check(21, "** Heading** leading space",
          '** Main Idea**Consider the following.',
          expected_substring='**Main Idea**\n\nConsider')

    # ─── SECTION F: Multiple headings in one block ───

    print("\n--- F: Multiple headings in a single text block ---")

    check(22, "Three consecutive headings with text",
          '**Intro**The verse says...**Analysis**Ibn Kathir noted...**Conclusion**In summary...',
          expected_substring=['**Intro**\n\nThe verse', '**Analysis**\n\nIbn Kathir', '**Conclusion**\n\nIn summary'])

    check(23, "Heading at very start and very end",
          '**Opening**First paragraph.**Closing**Final words.',
          expected_substring=['**Opening**\n\nFirst', '**Closing**\n\nFinal'])

    # ─── SECTION G: __underscore__ bold variant ───

    print("\n--- G: __underscore__ bold syntax ---")

    check(24, "__Heading__Text smashed together",
          '__Important Point__The scholars agreed...',
          expected_substring='__Important Point__\n\nThe',
          must_not_contain='__Important Point__The')

    check(25, "Text before __Heading__",
          'This ends a point.__Next Topic__It continues...',
          expected_substring='point.\n\n__Next Topic__\n\nIt')

    check(26, "__ Heading __ with spaces",
          '__ Spaced Heading __The content follows.',
          expected_substring='__Spaced Heading__\n\nThe')

    # ─── SECTION H: Edge cases / empty / special ───

    print("\n--- H: Edge cases ---")

    check(27, "Empty string",
          '',
          expected_exact='')

    check(28, "None input",
          None,
          expected_exact=None)

    check(29, "No bold markers at all",
          'Just a plain paragraph with no formatting whatsoever.',
          expected_exact='Just a plain paragraph with no formatting whatsoever.')

    check(30, "Only bold, no surrounding text",
          '**Standalone Heading**',
          expected_exact='**Standalone Heading**')

    check(31, "Bold in the middle of a sentence (should NOT break)",
          'The scholar **Ibn Kathir** said this about the verse.',
          must_not_contain='\n')

    check(32, "Asterisks that aren't bold (single *)",
          'This * is not bold * text.',
          expected_exact='This * is not bold * text.')

    check(33, "Very long heading",
          '**This Is A Very Long Bold Heading That Goes On And On About The Topic At Hand**The text.',
          expected_substring='\n\nThe text.')

    # ─── SECTION I: Realistic Gemini output patterns ───

    print("\n--- I: Realistic Gemini LLM output patterns ---")

    check(34, "Gemini tafsir output pattern: heading+text blob",
          '**The Magnificence of the Throne Verse (Ayat al-Kursi)**Ayat al-Kursi (2:255) is considered the greatest verse in the Quran. The Prophet Muhammad (peace be upon him) said to Ubayy ibn Ka\'b: "Which verse is the greatest?" He replied with this verse.',
          expected_substring='**The Magnificence of the Throne Verse (Ayat al-Kursi)**\n\nAyat al-Kursi',
          must_not_contain='Kursi)**Ayat')

    check(35, "Gemini multi-section pattern",
          '**Overview**The Fatiha is the opening chapter.**Linguistic Analysis**The word "hamd" means praise.**Spiritual Significance**This surah teaches the believer to acknowledge Allah\'s lordship.',
          expected_substring=['**Overview**\n\nThe Fatiha', '**Linguistic Analysis**\n\nThe word', '**Spiritual Significance**\n\nThis surah'])

    check(36, "Gemini output with Arabic transliteration",
          '**Tafsir of "Bismillah"**The phrase "Bismillahi ar-Rahmani ar-Raheem" means "In the Name of Allah, the Most Gracious, the Most Merciful."',
          expected_substring='**Tafsir of "Bismillah"**\n\nThe phrase')

    check(37, "Gemini output with hadith references",
          '**Hadith Evidence**The Prophet (peace be upon him) said: "Whoever recites Ayat al-Kursi after every prayer, nothing prevents him from entering Paradise except death." (An-Nasa\'i)**Scholar Commentary**Ibn Kathir explains...',
          expected_substring=['**Hadith Evidence**\n\nThe Prophet', '**Scholar Commentary**\n\nIbn Kathir'])

    check(38, "Gemini output with verse numbers",
          '**Verse 2:255 — The Throne Verse**"Allah — there is no deity except Him, the Ever-Living, the Self-Sustaining." This verse contains the greatest of Allah\'s Names.',
          expected_substring='**Verse 2:255 — The Throne Verse**\n\n"Allah')

    check(39, "Gemini bullets after heading",
          '**Key Themes**1. Monotheism (Tawhid)\n2. Divine attributes\n3. Intercession',
          expected_substring='**Key Themes**\n\n1. Monotheism')

    # ─── SECTION J: Pipeline tests (sanitize_explanation_text → sanitize_heading_format) ───

    print("\n--- J: Full pipeline (explanation_text + heading_format) ---")

    check(40, "Pipeline: excessive indent + smashed heading",
          '        **Deep Analysis**This verse reveals...',
          expected_substring='**Deep Analysis**\n\nThis verse',
          use_pipeline=True)

    check(41, "Pipeline: 8-space indent throughout",
          '        **First Point**\n        Text with indent.\n        **Second Point**\n        More text.',
          expected_substring=['**First Point**\n\n', '**Second Point**\n\n'],
          use_pipeline=True)

    check(42, "Pipeline: mixed indent + missing breaks",
          '    **Heading One**Text.\n            **Heading Two**More text.',
          expected_substring=['**Heading One**\n\nText', '**Heading Two**\n\nMore text'],
          use_pipeline=True)

    # ─── SECTION K: Boundary / regression tests ───

    print("\n--- K: Boundary and regression tests ---")

    check(43, "Bold word inside sentence should NOT break (short bold)",
          'He was a **great** scholar of his time.',
          must_not_contain='\n')

    check(44, "Two bold words in a sentence",
          'Both **Ibn Kathir** and **al-Qurtubi** agree on this.',
          must_not_contain='\n')

    check(45, "Heading ending with punctuation inside bold",
          '**What does this mean?**The answer is...',
          expected_substring='**What does this mean?**\n\nThe answer')

    check(46, "Heading with numbers inside",
          '**Point 3: The Third Pillar**Islam teaches...',
          expected_substring='**Point 3: The Third Pillar**\n\nIslam')

    check(47, "Semicolon before heading",
          'first topic covered;**Second Topic**The next area...',
          expected_substring='covered;\n\n**Second Topic**\n\nThe')

    check(48, "Comma before heading (should break)",
          'as mentioned above,**Additional Context**The Prophet...',
          expected_substring='above,\n\n**Additional Context**\n\nThe')

    check(49, "Star at end of bold before heading",
          'Read this verse.**Important**Do not skip it.',
          expected_substring=['verse.\n\n**Important**\n\nDo'])

    check(50, "Complex realistic blob — full Gemini response simulation",
          '**Overview of Surah Al-Fatiha**Surah Al-Fatiha, also known as "The Opening," is the first chapter of the Quran. It consists of seven verses and is recited in every unit of prayer.**Linguistic Analysis**The Arabic word "Fatiha" comes from the root "f-t-h" meaning "to open." The surah opens the Quran both physically and spiritually.**Themes and Structure**The surah can be divided into three parts: praise of Allah (verses 1-3), worship and seeking help (verse 4), and supplication for guidance (verses 5-7).**Connection to Prayer**The Prophet (peace be upon him) said: "There is no prayer for the one who does not recite the Fatiha of the Book." This hadith establishes the indispensable nature of this surah in Islamic worship.',
          expected_substring=[
              '**Overview of Surah Al-Fatiha**\n\nSurah Al-Fatiha',
              '**Linguistic Analysis**\n\nThe Arabic word',
              '**Themes and Structure**\n\nThe surah can',
              '**Connection to Prayer**\n\nThe Prophet'
          ],
          must_not_contain=['Fatiha**Surah', 'Analysis**The Arabic', 'Structure**The surah', 'Prayer**The Prophet'])

    # ─── RESULTS ───
    print("\n" + "=" * 70)
    print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
    print("=" * 70)

    if ERRORS:
        print(f"\n--- {len(ERRORS)} FAILURE DETAILS ---\n")
        for num, desc, reason, inp, result in ERRORS:
            print(f"Test #{num}: {desc}")
            print(f"  Reason: {reason}")
            print(f"  Input:  {repr(inp[:120])}{'...' if inp and len(inp) > 120 else ''}")
            print(f"  Output: {repr(result[:120]) if isinstance(result, str) else result}{'...' if isinstance(result, str) and len(result) > 120 else ''}")
            print()

    return FAIL == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
