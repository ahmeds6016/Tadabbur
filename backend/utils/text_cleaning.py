from typing import Any, Dict, List, Optional, Tuple
import re


def sanitize_heading_format(text: str) -> str:
    """
    Insert line break after bold subheadings when followed by text.

    Handles both **Bold** and __Bold__ markdown syntax.
    Uses \\s+ to match ANY whitespace (including non-breaking spaces from LLM).
    The frontend uses remark-breaks to render \\n as <br>.
    """
    if not text:
        return text

    # Pattern 1: **Any Bold Text** followed by whitespace and then text
    # Using \s+ instead of space to catch non-breaking spaces (\u00A0) from LLM
    if '**' in text:
        pattern_asterisk = r'(\*\*[^*]+\*\*)\s+([A-Za-z0-9\'\"\(\[])'
        prev = None
        while prev != text:
            prev = text
            text = re.sub(pattern_asterisk, lambda m: m.group(1) + '\n' + m.group(2), text)

    # Pattern 2: __Any Bold Text__ followed by whitespace and then text
    if '__' in text:
        pattern_underscore = r'(__[^_]+__)\s+([A-Za-z0-9\'\"\(\[])'
        prev = None
        while prev != text:
            prev = text
            text = re.sub(pattern_underscore, lambda m: m.group(1) + '\n' + m.group(2), text)

    return text
