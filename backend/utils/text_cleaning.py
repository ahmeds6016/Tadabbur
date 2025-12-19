from typing import Any, Dict, List, Optional, Tuple


def sanitize_heading_format(text: str) -> str:
    """
    Ensure ## headings are on their own line with proper spacing.

    IMPORTANT: This function does NOT convert **Bold** to ## headings.
    **Bold** sub-headers are the preferred format and should be kept as-is.

    This function only handles cases where the LLM generates inline ## headings
    like "text. ## Heading more text" - it splits these onto separate lines.
    """
    if not text:
        return text

    import re

    # If no ## headings exist, return text unchanged (most common case)
    if '##' not in text:
        return text

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
