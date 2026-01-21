from typing import Any, Dict, List, Optional, Tuple
import re


def sanitize_heading_format(text: str) -> str:
    """
    Insert line breaks BEFORE and AFTER bold subheadings.

    Handles both **Bold** and __Bold__ markdown syntax.
    Uses robust patterns to match various whitespace types (spaces, tabs, non-breaking spaces).
    """
    if not text:
        return text

    if '**' in text:
        # BEFORE heading: punctuation + any whitespace + ** → punctuation + \n\n + **
        before_pattern = re.compile(r'([.?!])[ \t\u00a0]+(\*\*)')
        text = before_pattern.sub(r'\1\n\n\2', text)

        # Handle case with NO space between punctuation and **
        no_space_pattern = re.compile(r'([.?!])(\*\*[A-Za-z])')
        text = no_space_pattern.sub(r'\1\n\n\2', text)

        # AFTER heading: **text** + whitespace + word → **text** + \n\n + word
        after_pattern = re.compile(r'(\*\*.+?\*\*)[ \t\u00a0]+([A-Za-z0-9\'\"\(])')
        text = after_pattern.sub(r'\1\n\n\2', text)

    if '__' in text:
        # BEFORE heading for underscore syntax
        before_underscore = re.compile(r'([.?!])[ \t\u00a0]+(__)')
        text = before_underscore.sub(r'\1\n\n\2', text)

        # AFTER heading for underscore syntax
        after_underscore = re.compile(r'(__.+?__)[ \t\u00a0]+([A-Za-z0-9\'\"\(])')
        text = after_underscore.sub(r'\1\n\n\2', text)

    return text
