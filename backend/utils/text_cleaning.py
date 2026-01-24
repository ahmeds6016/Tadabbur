from typing import Any, Dict, List, Optional, Tuple
import re


def sanitize_heading_format(text: str) -> str:
    """
    Insert line breaks BEFORE and AFTER bold subheadings.

    Handles both **Bold** and __Bold__ markdown syntax.
    """
    if not text:
        return text

    if '**' in text:
        # STEP 0: Normalize - remove spaces after ** and before **
        # LLM sometimes generates "** Heading **" instead of "**Heading**"
        text = re.sub(r'\*\*\s+', '**', text)
        text = re.sub(r'\s+\*\*', '**', text)

        # STEP 1: Add \n\n AFTER **heading**
        text = re.sub(r'(\*\*[^*]+\*\*)[ \t]*([A-Za-z])', r'\1\n\n\2', text)

        # STEP 2: Add \n\n BEFORE **heading**
        text = re.sub(r'([.?!:;,\)\]\'\"])[ \t]*(\*\*[A-Z])', r'\1\n\n\2', text)

        # STEP 3: Handle existing single \n
        text = re.sub(r'(\*\*[^*]+\*\*)\n([A-Za-z])', r'\1\n\n\2', text)
        text = re.sub(r'([.?!:;,\)\]\'\"])\n(\*\*[A-Z])', r'\1\n\n\2', text)

        # Cleanup
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')

    if '__' in text:
        text = re.sub(r'__\s+', '__', text)
        text = re.sub(r'\s+__', '__', text)
        text = re.sub(r'(__.+?__)[ \t]*([A-Za-z])', r'\1\n\n\2', text)
        text = re.sub(r'([.?!:;,\)\]\'\"])[ \t]*(__[A-Z])', r'\1\n\n\2', text)
        text = re.sub(r'(__.+?__)\n([A-Za-z])', r'\1\n\n\2', text)
        text = re.sub(r'([.?!:;,\)\]\'\"])\n(__[A-Z])', r'\1\n\n\2', text)
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')

    return text
