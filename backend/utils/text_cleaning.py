from typing import Any, Dict, List, Optional, Tuple
import re


def sanitize_heading_format(text: str) -> str:
    """
    Insert line break after **Bold** subheadings when followed by text.

    The LLM generates **Bold** headings but doesn't always add line breaks.
    The frontend uses remark-breaks to render \n as <br>.
    This function ensures there's a \n after bold headings.
    """
    if not text or '**' not in text:
        return text

    # Pattern: **Any Bold Text** followed by space(s) and then a word character
    # This catches: "**Heading** The text continues..."
    # But not: "**Heading**\nThe text..." (already has line break)
    # And not: "**Heading**" at end of text
    pattern = r'(\*\*[^*]+\*\*) +([A-Za-z0-9\'\"\(])'

    def add_linebreak(match):
        return match.group(1) + '\n' + match.group(2)

    # Apply until no more matches (handles multiple headings)
    prev = None
    while prev != text:
        prev = text
        text = re.sub(pattern, add_linebreak, text)

    return text
