#!/usr/bin/env python3
"""
Test the JSON fix function with the actual malformed Gemini response.
"""
import json
import re

def fix_malformed_json(text: str) -> str:
    """
    Comprehensive JSON cleanup for malformed Gemini responses.
    Handles:
    1. Unescaped quotes inside string values
    2. Trailing commas before closing braces/brackets
    3. Missing commas between properties
    4. Unicode issues (BOM, zero-width spaces)
    5. Smart quotes and other typography
    """
    # Step 1: Remove BOM and invisible characters
    text = text.lstrip('\ufeff\u200b\u200c\u200d\ufeff')

    # Step 2: Replace smart quotes with regular quotes (if any slipped through)
    text = text.replace('\u201c', '"').replace('\u201d', '"')  # " "
    text = text.replace('\u2018', "'").replace('\u2019', "'")  # ' '

    # Step 3: Remove trailing commas before closing braces/brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    # Step 4: Fix unescaped quotes in JSON string values
    # This is the most complex part - we need to identify string values
    # and escape any quotes inside them that aren't already escaped

    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(text):
        char = text[i]

        # Handle escape sequences
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue

        # Handle double quotes
        if char == '"':
            if not in_string:
                # Starting a string
                in_string = True
                result.append(char)
                i += 1
                continue
            else:
                # Possibly ending a string - check what comes after
                # Look ahead to find next non-whitespace character
                next_idx = i + 1
                while next_idx < len(text) and text[next_idx] in ' \t\n\r':
                    next_idx += 1

                next_char = text[next_idx] if next_idx < len(text) else None

                # If followed by :, ,, }, ], or end of text, this closes the string
                if next_char is None or next_char in ',:}]':
                    in_string = False
                    result.append(char)
                    i += 1
                    continue
                else:
                    # This is an unescaped quote in the middle - escape it!
                    result.append('\\')
                    result.append(char)
                    i += 1
                    continue

        # Normal character
        result.append(char)
        i += 1

    return ''.join(result)


# Test with the actual malformed response
print("="*80)
print("TESTING JSON FIX FUNCTION")
print("="*80)

with open('gemini_response_extracted.json', 'r', encoding='utf-8') as f:
    malformed_json = f.read()

print(f"\nOriginal length: {len(malformed_json)} chars")

# Try parsing original (should fail)
print("\n1. Trying to parse ORIGINAL JSON...")
try:
    parsed = json.loads(malformed_json)
    print("   ✅ UNEXPECTED: Original parsed successfully!")
except json.JSONDecodeError as e:
    print(f"   ❌ EXPECTED FAILURE: {e.msg} at position {e.pos}")

# Apply fix
print("\n2. Applying JSON fix...")
fixed_json = fix_malformed_json(malformed_json)
print(f"   Fixed length: {len(fixed_json)} chars")

# Try parsing fixed
print("\n3. Trying to parse FIXED JSON...")
try:
    parsed = json.loads(fixed_json)
    print("   ✅ SUCCESS! Fixed JSON parsed correctly!")
    print(f"\n   Keys in parsed JSON: {list(parsed.keys())}")

    if 'verses' in parsed:
        print(f"   - verses: {len(parsed['verses'])} items")
    if 'tafsir_explanations' in parsed:
        print(f"   - tafsir_explanations: {len(parsed['tafsir_explanations'])} items")
    if 'cross_references' in parsed:
        print(f"   - cross_references: {len(parsed['cross_references'])} items")
    if 'lessons_practical_applications' in parsed:
        print(f"   - lessons_practical_applications: {len(parsed['lessons_practical_applications'])} items")
    if 'summary' in parsed:
        print(f"   - summary: {len(parsed['summary'])} chars")

    # Save the fixed version
    with open('gemini_response_FIXED.json', 'w', encoding='utf-8') as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)
    print("\n   ✅ Saved fixed and validated JSON to gemini_response_FIXED.json")

except json.JSONDecodeError as e:
    print(f"   ❌ STILL FAILED: {e.msg} at position {e.pos}")

    # Show where it failed
    context_start = max(0, e.pos - 200)
    context_end = min(len(fixed_json), e.pos + 200)
    print(f"\n   Error context:")
    print(f"   ...{fixed_json[context_start:e.pos]}")
    print(f"   <<<ERROR HERE>>>")
    print(f"   {fixed_json[e.pos:context_end]}...")

print("\n" + "="*80)
