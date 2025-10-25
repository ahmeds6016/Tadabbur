#!/usr/bin/env python3
"""
Extract the Gemini JSON response from log file and diagnose parsing error.
"""
import json

# Read the log file
with open('downloaded-logs-20251020-222648.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Parse the JSON array
logs = json.loads(content)

# Extract lines 1375-2774 (0-indexed: 1374-2773)
start_idx = 1374
end_idx = min(2773, len(logs) - 1)  # Don't exceed array bounds

print(f"Total logs in file: {len(logs)}")
print(f"Extracting logs from index {start_idx} to {end_idx}")

# Reconstruct the complete Gemini response from textPayload fields
gemini_response_lines = []
for i in range(start_idx, end_idx + 1):
    if i < len(logs) and 'textPayload' in logs[i]:
        gemini_response_lines.append(logs[i]['textPayload'])

# Join all lines to form the complete JSON response
gemini_response_text = '\n'.join(gemini_response_lines)

print("="*80)
print("COMPLETE GEMINI RESPONSE (reconstructed from logs)")
print("="*80)
print(gemini_response_text)
print("="*80)
print(f"\nTotal characters: {len(gemini_response_text)}")
print(f"Total lines: {len(gemini_response_lines)}")
print("="*80)

# Now try to parse it and identify the exact error
print("\nATTEMPTING TO PARSE JSON...")
print("="*80)

try:
    parsed = json.loads(gemini_response_text)
    print("✅ SUCCESS! JSON parsed successfully")
    print(f"\nKeys in parsed JSON: {list(parsed.keys())}")
    if 'verses' in parsed:
        print(f"Number of verses: {len(parsed['verses'])}")
    if 'tafsir_explanations' in parsed:
        print(f"Number of tafsir explanations: {len(parsed['tafsir_explanations'])}")
except json.JSONDecodeError as e:
    print(f"❌ PARSE FAILED!")
    print(f"\nError: {e.msg}")
    print(f"Position: {e.pos}")
    print(f"Line: {e.lineno}")
    print(f"Column: {e.colno}")

    # Show context around error
    if e.pos < len(gemini_response_text):
        context_start = max(0, e.pos - 200)
        context_end = min(len(gemini_response_text), e.pos + 200)

        print("\n" + "="*80)
        print("ERROR CONTEXT (200 chars before/after)")
        print("="*80)
        before = gemini_response_text[context_start:e.pos]
        after = gemini_response_text[e.pos:context_end]

        print(before)
        print(" <<<ERROR_HERE>>> ")
        print(after)
        print("="*80)

        # Show the specific character at error position
        if e.pos < len(gemini_response_text):
            error_char = gemini_response_text[e.pos]
            print(f"\nCharacter at error position: '{error_char}' (ASCII: {ord(error_char)})")
