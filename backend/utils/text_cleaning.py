from typing import Any, Dict, List, Optional, Tuple
import re


def sanitize_heading_format(text: str) -> str:
    """
    Ensure headings (## and **Bold**) are on their own line with proper spacing.

    Handles:
    1. ## Markdown headings - ensures they're on their own line
    2. **Bold subheadings** - ensures line break after them when followed by text

    Patterns for bold subheadings that need line breaks:
    - **Verse 1: Some Text** followed by paragraph text
    - **Context of Revelation** followed by paragraph text
    - **Some Heading:** followed by paragraph text
    """
    if not text:
        return text

    # First pass: Handle ## headings
    if '##' in text:
        text = _handle_hash_headings(text)

    # Second pass: Handle **Bold** subheadings that are inline with text
    text = _handle_bold_subheadings(text)

    return text


def _handle_hash_headings(text: str) -> str:
    """Handle ## markdown headings - ensure they're on their own line."""
    processed_lines = []

    for line in text.split('\n'):
        stripped = line.strip()

        # Preserve blank lines
        if stripped == '':
            processed_lines.append('')
            continue

        # Check if line contains ## (either at start or inline)
        if '##' in stripped:
            # Handle inline ## headings - split before and after
            if not stripped.startswith('##'):
                # Inline ## - split the line
                before, after = stripped.split('##', 1)
                before = before.rstrip()

                if before:
                    processed_lines.append(before)
                    processed_lines.append('')  # Blank line before heading

                # The heading and any text after it
                heading_line = '## ' + after.strip()
                processed_lines.append(heading_line)
                processed_lines.append('')  # Blank line after heading
            else:
                # ## at start of line - ensure proper spacing
                if processed_lines and processed_lines[-1].strip():
                    processed_lines.append('')  # Blank line before heading
                processed_lines.append(stripped)
                processed_lines.append('')  # Blank line after heading
        else:
            # No ## in this line, keep as-is
            processed_lines.append(line)

    # Collapse multiple consecutive blank lines
    cleaned_lines = []
    for line in processed_lines:
        if line == '' and (not cleaned_lines or cleaned_lines[-1] == ''):
            continue
        cleaned_lines.append(line)

    # Remove trailing blank line
    while cleaned_lines and cleaned_lines[-1] == '':
        cleaned_lines.pop()

    return '\n'.join(cleaned_lines)


def _handle_bold_subheadings(text: str) -> str:
    """
    Handle **Bold** subheadings that are inline with paragraph text.

    Patterns to match:
    - **Verse N: Text (Translation)** followed by explanation text
    - **Some Heading** followed by explanation text (when heading ends with **)
    - **Heading:** followed by text

    We insert a line break after the bold subheading.
    """
    if '**' not in text:
        return text

    # Pattern: **Verse N: Arabic (Translation)** followed by text
    # Example: **Verse 1: Qul Huwa... (Say, "He is...")** Ibn Kathir elucidates...
    verse_pattern = r'(\*\*Verse \d+:[^*]+\*\*)\s+([A-Z\'\"])'

    # Pattern: **Heading Title** followed by text (heading doesn't end with :)
    # Example: **Context of Revelation** This Surah was revealed...
    # Also handles: **The Name 'Allah'** 'Allah' is... (text starting with quote)
    heading_pattern = r'(\*\*[A-Z][^*:]+\*\*)\s+([A-Z\'\"])'

    # Pattern: **Heading:** followed by text
    # Example: **Analysis:** The verse states...
    colon_heading_pattern = r'(\*\*[^*]+:\*\*)\s+([A-Z\'\"])'

    def add_linebreak(match):
        return match.group(1) + '\n\n' + match.group(2)

    # Apply patterns in order of specificity
    text = re.sub(verse_pattern, add_linebreak, text)
    text = re.sub(colon_heading_pattern, add_linebreak, text)
    text = re.sub(heading_pattern, add_linebreak, text)

    return text
