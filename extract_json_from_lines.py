#!/usr/bin/env python3
"""
Extract Gemini JSON from specific line numbers in the log file.
"""
import json
import re

# Read lines 1375-2775 from the file
with open('downloaded-logs-20251020-222648.json', 'r', encoding='utf-8') as f:
    all_lines = f.readlines()

# Extract lines 1375-2775 (1-indexed, so 1374-2774 in 0-indexed)
start_line = 1374  # 0-indexed
end_line = 2774    # 0-indexed

log_lines = all_lines[start_line:end_line+1]

# Now parse each JSON log entry and extract textPayload
gemini_response_parts = []
for line in log_lines:
    line = line.strip()
    if not line or line in ['{', '}', ',']:
        continue

    # Try to find textPayload in the line
    if '"textPayload":' in line:
        # Extract the value after textPayload
        match = re.search(r'"textPayload":\s*"(.+)"', line)
        if match:
            # Get the JSON-escaped string and unescape it
            payload = match.group(1)
            # Unescape JSON string
            try:
                unescaped = json.loads(f'"{payload}"')
                gemini_response_parts.append(unescaped)
            except:
                # Sometimes the line might be split
                gemini_response_parts.append(payload)

# Join all parts
gemini_response_text = '\n'.join(gemini_response_parts)

print("="*80)
print("COMPLETE GEMINI RESPONSE (reconstructed)")
print("="*80)
print(gemini_response_text)
print("="*80)
print(f"\nTotal characters: {len(gemini_response_text)}")
print(f"Total parts: {len(gemini_response_parts)}")
print("="*80)

# Save to file for inspection
with open('gemini_response_extracted.json', 'w', encoding='utf-8') as f:
    f.write(gemini_response_text)
print("\n✅ Saved to gemini_response_extracted.json")

# Try to parse
print("\nATTEMPTING TO PARSE JSON...")
print("="*80)

try:
    parsed = json.loads(gemini_response_text)
    print("✅ SUCCESS! JSON parsed successfully")
    print(f"\nKeys: {list(parsed.keys())}")
    if 'verses' in parsed:
        print(f"Verses: {len(parsed['verses'])}")
    if 'tafsir_explanations' in parsed:
        print(f"Tafsir explanations: {len(parsed['tafsir_explanations'])}")
except json.JSONDecodeError as e:
    print(f"❌ PARSE FAILED!")
    print(f"\nError: {e.msg}")
    print(f"Position: {e.pos}")
    print(f"Line: {e.lineno}, Column: {e.colno}")

    # Show context
    if e.pos < len(gemini_response_text):
        context_start = max(0, e.pos - 300)
        context_end = min(len(gemini_response_text), e.pos + 300)

        print("\n" + "="*80)
        print("ERROR CONTEXT (300 chars before/after)")
        print("="*80)
        before = gemini_response_text[context_start:e.pos]
        after = gemini_response_text[e.pos:context_end]

        print(before)
        print("\n<<< ERROR AT THIS POSITION >>>\n")
        print(after)
        print("="*80)

        if e.pos < len(gemini_response_text):
            error_char = gemini_response_text[e.pos]
            print(f"\nCharacter at error: repr='{repr(error_char)}', ASCII={ord(error_char)}")

            # Show surrounding characters
            print(f"\n5 characters before: {repr(gemini_response_text[max(0,e.pos-5):e.pos])}")
            print(f"Error character: {repr(error_char)}")
            print(f"5 characters after: {repr(gemini_response_text[e.pos+1:min(len(gemini_response_text),e.pos+6)])}")
