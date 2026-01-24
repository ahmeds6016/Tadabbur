from typing import Any, Dict, List, Optional, Tuple
import re


def sanitize_heading_format(text: str) -> str:
    """
    Insert line breaks BEFORE and AFTER bold subheadings.

    Handles both **Bold** and __Bold__ markdown syntax.
    Uses \s* to match ANY whitespace (including unicode spaces).
    """
    if not text:
        return text

    if '**' in text:
        # BEFORE: Add \n\n before **Heading** when preceded by punctuation
        before_pattern = re.compile(r'([.?!:;,\)\]\'\"])\s*(\*\*[A-Z])')
        text = before_pattern.sub(r'\1\n\n\2', text)

        # AFTER: Add \n\n after **Heading** when followed by letter
        after_pattern = re.compile(r'(\*\*[^*]+\*\*)\s*([A-Za-z])')
        text = after_pattern.sub(r'\1\n\n\2', text)

        # Prevent triple+ newlines
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')

    if '__' in text:
        # BEFORE heading for underscore syntax
        before_underscore = re.compile(r'([.?!:;,\)\]\'\"])\s*(__[A-Z])')
        text = before_underscore.sub(r'\1\n\n\2', text)

        # AFTER heading for underscore syntax
        after_underscore = re.compile(r'(__.+?__)\s*([A-Za-z])')
        text = after_underscore.sub(r'\1\n\n\2', text)

        # Prevent triple+ newlines
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')

    return text
