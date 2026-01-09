from typing import Any, Dict, List, Optional, Tuple
import re


def sanitize_heading_format(text: str) -> str:
    """
    Insert line break after bold subheadings when followed by text.

    Handles both **Bold** and __Bold__ markdown syntax.
    The frontend uses remark-breaks to render \n as <br>.
    """
    if not text:
        return text

    # Pattern 1: **Any Bold Text** followed by space(s) and then text
    if '**' in text:
        pattern_asterisk = r'(\*\*[^*]+\*\*) +([A-Za-z0-9\'\"\(\[])'
        prev = None
        while prev != text:
            prev = text
            text = re.sub(pattern_asterisk, lambda m: m.group(1) + '\n' + m.group(2), text)

    # Pattern 2: __Any Bold Text__ followed by space(s) and then text
    if '__' in text:
        pattern_underscore = r'(__[^_]+__) +([A-Za-z0-9\'\"\(\[])'
        prev = None
        while prev != text:
            prev = text
            text = re.sub(pattern_underscore, lambda m: m.group(1) + '\n' + m.group(2), text)

    return text
