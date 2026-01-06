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

    Adds a single line break after bold subheadings for 0.5 line spacing.
    Uses non-greedy matching to handle multiple headings on the same line.
    """
    if '**' not in text:
        return text

    # Generic pattern: Match any **Bold Text** followed by whitespace and then content
    # Uses non-greedy .*? to match content between ** pairs correctly
    # Matches when followed by any word character, quote, or opening paren
    # This handles all cases: **Heading** Text, **Verse 1: Arabic** Text, **Title:** Text
    bold_pattern = r'(\*\*[^*]+\*\*)\s+([A-Za-z0-9\'\"\(\[])'

    def add_linebreak(match):
        return match.group(1) + '\n' + match.group(2)

    # Apply the pattern - may need multiple passes for consecutive headings
    prev_text = None
    while prev_text != text:
        prev_text = text
        text = re.sub(bold_pattern, add_linebreak, text)

    return text
