#!/usr/bin/env python3
"""
Deep clean all tafsir source JSON files for universal consistency.

Fixes:
1. Smart/curly quotes → ASCII straight quotes
2. Non-breaking spaces → regular spaces
3. Unicode ellipsis → three dots
4. Double spaces in text values → single space
5. Leading/trailing whitespace in string values
6. Stray HTML tags → stripped (e.g., <b>, <strong>, <i>)
7. Stray markdown emphasis (***word***) → plain word
8. Normalize line endings
9. Remove zero-width characters
"""

import json
import os
import re
import sys

# --- Cleaning Rules ---

SMART_QUOTE_MAP = {
    '\u2018': "'",   # Left single curly quote
    '\u2019': "'",   # Right single curly quote (also used as apostrophe)
    '\u201A': "'",   # Single low-9 quotation mark
    '\u201B': "'",   # Single high-reversed-9 quotation mark
    '\u201C': '"',   # Left double curly quote
    '\u201D': '"',   # Right double curly quote
    '\u201E': '"',   # Double low-9 quotation mark
    '\u201F': '"',   # Double high-reversed-9 quotation mark
    '\u2039': "'",   # Single left-pointing angle quotation
    '\u203A': "'",   # Single right-pointing angle quotation
}

UNICODE_NORMALIZE_MAP = {
    '\u00A0': ' ',    # Non-breaking space
    '\u2026': '...',  # Horizontal ellipsis
    '\u200B': '',     # Zero-width space
    '\u200C': '',     # Zero-width non-joiner (keep for Arabic? Actually remove from English text)
    '\u200D': '',     # Zero-width joiner
    '\uFEFF': '',     # BOM / zero-width no-break space
    '\u00AD': '',     # Soft hyphen
}

# HTML tag pattern - matches <b>, </b>, <strong>, </strong>, <i>, </i>, <em>, </em>, etc.
HTML_TAG_PATTERN = re.compile(
    r'</?(?:b|strong|i|em|u|s|strike|del|ins|mark|small|big|sub|sup|br|hr|p|div|span|font|center|blockquote)(?:\s[^>]*)?>',
    re.IGNORECASE
)

# Markdown triple emphasis: ***word*** → word
TRIPLE_EMPHASIS_PATTERN = re.compile(r'\*{3}([^*]+)\*{3}')
# Markdown double emphasis: **word** → word (only in source data, not in prompts)
DOUBLE_EMPHASIS_PATTERN = re.compile(r'\*{2}([^*]+)\*{2}')
# Markdown single emphasis: *word* → word
SINGLE_EMPHASIS_PATTERN = re.compile(r'(?<!\*)\*([^*]+)\*(?!\*)')

# Multiple spaces → single space
MULTI_SPACE_PATTERN = re.compile(r' {2,}')


def clean_string(text: str) -> str:
    """Apply all cleaning rules to a single string value."""
    if not isinstance(text, str) or not text:
        return text

    # 1. Smart quotes → ASCII
    for smart, ascii_char in SMART_QUOTE_MAP.items():
        text = text.replace(smart, ascii_char)

    # 2. Unicode normalization (NBSP, ellipsis, zero-width chars)
    for char, replacement in UNICODE_NORMALIZE_MAP.items():
        text = text.replace(char, replacement)

    # 3. Strip HTML tags
    text = HTML_TAG_PATTERN.sub('', text)

    # 4. Remove markdown emphasis from source data
    #    (source data should be plain text - Gemini adds formatting)
    text = TRIPLE_EMPHASIS_PATTERN.sub(r'\1', text)
    text = DOUBLE_EMPHASIS_PATTERN.sub(r'\1', text)
    # Be careful with single * - only remove if it looks like emphasis, not multiplication
    text = SINGLE_EMPHASIS_PATTERN.sub(r'\1', text)

    # 5. Collapse multiple spaces into one
    text = MULTI_SPACE_PATTERN.sub(' ', text)

    # 6. Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 7. Strip leading/trailing whitespace
    text = text.strip()

    return text


def clean_value(value):
    """Recursively clean all string values in a JSON structure."""
    if isinstance(value, str):
        return clean_string(value)
    elif isinstance(value, list):
        return [clean_value(item) for item in value]
    elif isinstance(value, dict):
        return {key: clean_value(val) for key, val in value.items()}
    else:
        return value  # Numbers, booleans, null


def process_file(filepath: str, dry_run: bool = False) -> dict:
    """Process a single JSON file. Returns stats dict."""
    stats = {
        'file': os.path.basename(filepath),
        'smart_quotes_fixed': 0,
        'unicode_fixed': 0,
        'html_tags_removed': 0,
        'markdown_stripped': 0,
        'spaces_collapsed': 0,
        'verses_processed': 0,
    }

    with open(filepath, 'r', encoding='utf-8') as f:
        original_text = f.read()

    # Count issues before cleaning
    for char in SMART_QUOTE_MAP:
        stats['smart_quotes_fixed'] += original_text.count(char)

    for char in ['\u00A0', '\u2026', '\u200B', '\u200C', '\u200D', '\uFEFF', '\u00AD']:
        stats['unicode_fixed'] += original_text.count(char)

    stats['html_tags_removed'] = len(HTML_TAG_PATTERN.findall(original_text))
    stats['markdown_stripped'] = len(TRIPLE_EMPHASIS_PATTERN.findall(original_text)) + \
                                  len(DOUBLE_EMPHASIS_PATTERN.findall(original_text))

    # Parse, clean, and write
    data = json.loads(original_text)

    verses = data.get('verses', [])
    stats['verses_processed'] = len(verses)

    cleaned_data = clean_value(data)

    if not dry_run:
        cleaned_json = json.dumps(cleaned_data, ensure_ascii=False, indent=2)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned_json + '\n')

        print(f"  ✅ Written: {filepath}")
    else:
        print(f"  🔍 Dry run: {filepath}")

    return stats


def main():
    dry_run = '--dry-run' in sys.argv

    source_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'tafsir_sources')
    source_dir = os.path.abspath(source_dir)

    # Process main files (these are what get uploaded to GCS)
    json_files = sorted([
        os.path.join(source_dir, f)
        for f in os.listdir(source_dir)
        if f.endswith('.json') and os.path.isfile(os.path.join(source_dir, f))
    ])

    # Also process cleaned/ directory
    cleaned_dir = os.path.join(source_dir, 'cleaned')
    if os.path.isdir(cleaned_dir):
        json_files.extend(sorted([
            os.path.join(cleaned_dir, f)
            for f in os.listdir(cleaned_dir)
            if f.endswith('.json') and os.path.isfile(os.path.join(cleaned_dir, f))
        ]))

    if not json_files:
        print("ERROR: No JSON files found!")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Deep Cleaning Tafsir Source Files")
    print(f"{'='*60}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE (writing files)'}")
    print(f"Files: {len(json_files)}")
    print(f"{'='*60}\n")

    total_stats = {
        'smart_quotes_fixed': 0,
        'unicode_fixed': 0,
        'html_tags_removed': 0,
        'markdown_stripped': 0,
        'verses_processed': 0,
        'files_processed': 0,
    }

    for filepath in json_files:
        rel_path = os.path.relpath(filepath, source_dir)
        print(f"\nProcessing: {rel_path}")
        stats = process_file(filepath, dry_run=dry_run)

        total_stats['files_processed'] += 1
        for key in ['smart_quotes_fixed', 'unicode_fixed', 'html_tags_removed',
                     'markdown_stripped', 'verses_processed']:
            total_stats[key] += stats[key]

        # Print per-file stats
        issues = []
        if stats['smart_quotes_fixed']:
            issues.append(f"smart quotes: {stats['smart_quotes_fixed']}")
        if stats['unicode_fixed']:
            issues.append(f"unicode chars: {stats['unicode_fixed']}")
        if stats['html_tags_removed']:
            issues.append(f"HTML tags: {stats['html_tags_removed']}")
        if stats['markdown_stripped']:
            issues.append(f"markdown emphasis: {stats['markdown_stripped']}")

        if issues:
            print(f"  Fixed: {', '.join(issues)}")
        else:
            print(f"  Clean! No issues found.")
        print(f"  Verses: {stats['verses_processed']}")

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Files processed:    {total_stats['files_processed']}")
    print(f"Verses processed:   {total_stats['verses_processed']}")
    print(f"Smart quotes fixed: {total_stats['smart_quotes_fixed']}")
    print(f"Unicode chars fixed:{total_stats['unicode_fixed']}")
    print(f"HTML tags removed:  {total_stats['html_tags_removed']}")
    print(f"Markdown stripped:  {total_stats['markdown_stripped']}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
