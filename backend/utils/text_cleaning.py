from typing import Any, Dict, List, Optional, Tuple


def sanitize_heading_format(text: str) -> str:
    """
    Convert bold text at the start of lines into proper markdown headings AND
    ensure ## headings are always on their own line with proper spacing.

    Fixes two issues:
    1. LLM generates **Header** instead of ## Header
    2. LLM generates inline headings like "text. ## Header more text"
    """
    if not text:
        return text

    import re

    def add_blank_line(processed: List[str]) -> None:
        """Insert a single blank line if the previous line isn't already blank."""
        if processed and processed[-1].strip():
            processed.append('')

    def split_heading_and_body(raw_heading: str) -> Tuple[str, str]:
        """
        Separate a heading from any trailing body text that may have been kept
        on the same line (e.g., '## Heading While the verse declares...').
        """
        heading_content = raw_heading.strip()
        if not heading_content:
            return "", ""

        boundary_positions = []

        # Punctuation followed by capital letter often marks the start of body text
        punctuation_match = re.search(r'[.?!:]\s+[A-Z]', heading_content)
        if punctuation_match:
            boundary_positions.append(punctuation_match.start())

        # Common sentence starters that indicate body text
        sentence_starters = [
            ' While ', ' The ', ' This ', ' It ', ' Ibn ', ' He ', ' She ',
            ' They ', ' These ', ' Those ', ' When ', ' If ', ' As ', ' In ', ' For '
        ]
        for starter in sentence_starters:
            pos = heading_content.find(starter)
            if pos > 0:
                boundary_positions.append(pos)

        if boundary_positions:
            split_at = min(boundary_positions)
            return heading_content[:split_at].strip(' .:;-'), heading_content[split_at:].strip()

        # Fallback: split at first space to avoid headings swallowing body text
        if ' ' in heading_content:
            first_space = heading_content.find(' ')
            return heading_content[:first_space].strip(' .:;-'), heading_content[first_space:].strip()

        return heading_content, ""

    processed_lines = []

    for line in text.split('\n'):
        stripped = line.strip()

        # Preserve blank lines
        if stripped == '':
            processed_lines.append('')
            continue

        # Convert **Header** (at start of line) to ## Header
        if stripped.startswith('**') and '**' in stripped[2:]:
            end_pos = stripped.find('**', 2)
            if end_pos != -1:
                heading_text = stripped[2:end_pos].strip()
                rest_of_line = stripped[end_pos + 2:].strip()

                add_blank_line(processed_lines)
                if heading_text:
                    processed_lines.append(f"## {heading_text}")
                processed_lines.append('')
                if rest_of_line:
                    processed_lines.append(rest_of_line)
                continue

        # Headings already at line start but possibly with trailing text
        if stripped.startswith('##'):
            heading_text, trailing_text = split_heading_and_body(stripped[2:])
            add_blank_line(processed_lines)
            if heading_text:
                processed_lines.append(f"## {heading_text}")
            processed_lines.append('')
            if trailing_text:
                processed_lines.append(trailing_text)
            continue

        # Inline headings embedded within a paragraph
        if '##' in stripped:
            before, after = stripped.split('##', 1)
            before = before.rstrip()
            heading_text, trailing_text = split_heading_and_body(after)

            if before:
                processed_lines.append(before)

            add_blank_line(processed_lines)
            if heading_text:
                processed_lines.append(f"## {heading_text}")

            processed_lines.append('')
            if trailing_text:
                processed_lines.append(trailing_text)
            continue

        # No conversion needed
        processed_lines.append(line)

    # Collapse multiple consecutive blank lines
    cleaned_lines = []
    for line in processed_lines:
        if line == '' and (not cleaned_lines or cleaned_lines[-1] == ''):
            continue
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)
