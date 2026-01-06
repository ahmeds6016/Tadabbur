from typing import Any, Dict, List, Optional, Tuple
import re


def sanitize_heading_format(text: str) -> str:
    """
    Pass-through function - LLM handles formatting directly.

    Reverted to cc8083f behavior where the LLM's output is used as-is
    without post-processing. The prompt already instructs the LLM to
    format headings with **Bold** and proper line breaks.
    """
    return text if text else text
