from typing import Any, Dict, List, Optional, Tuple
import re


def normalize_html_to_markdown(text: str) -> str:
    """
    Convert HTML tags in LLM output to their markdown equivalents.

    Gemini sometimes outputs <b>, <strong>, <i>, <em> etc. despite being
    told to use **markdown bold**. This normalizes everything to markdown
    so the frontend ReactMarkdown renderer handles it consistently.
    """
    if not text:
        return text

    # Bold: <b>text</b> or <strong>text</strong> → **text**
    text = re.sub(r'<(?:b|strong)>(.*?)</(?:b|strong)>', r'**\1**', text, flags=re.DOTALL)

    # Italic: <i>text</i> or <em>text</em> → *text*
    text = re.sub(r'<(?:i|em)>(.*?)</(?:i|em)>', r'*\1*', text, flags=re.DOTALL)

    # Line breaks: <br>, <br/>, <br /> → newline
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)

    # Headings: <h3>text</h3> → **text**
    text = re.sub(r'<h[1-6]>(.*?)</h[1-6]>', r'**\1**', text, flags=re.DOTALL)

    # Strip any remaining HTML tags (span, div, p, font, etc.)
    text = re.sub(r'</?(?:span|div|p|font|center|u|s|mark|small|big|sub|sup|blockquote|ul|ol|li|table|tr|td|th)(?:\s[^>]*)?>', '', text, flags=re.IGNORECASE)

    return text


def sanitize_heading_format(text: str) -> str:
    """
    Insert line breaks BEFORE and AFTER bold subheadings.

    Handles both **Bold** and __Bold__ markdown syntax.
    Ensures headings like **Title**"Text..." or **Title**The text...
    always have proper \\n\\n separation.
    """
    if not text:
        return text

    if '**' in text:
        # STEP 0: Normalize - remove spaces after ** and before **
        # LLM sometimes generates "** Heading **" instead of "**Heading**"
        text = re.sub(r'\*\*\s+', '**', text)
        text = re.sub(r'\s+\*\*', '**', text)

        # STEP 1: Add \n\n AFTER **heading** when followed by any content character
        # Matches letters, quotes, digits, parentheses — any non-whitespace start
        text = re.sub(r'(\*\*[^*]+\*\*)[ \t]*([A-Za-z0-9"\'\(\[`])', r'\1\n\n\2', text)

        # STEP 2: Add \n\n BEFORE **heading** when preceded by sentence-ending punct
        text = re.sub(r'([.?!:;,\)\]\'\"\*])[ \t]*(\*\*[A-Z])', r'\1\n\n\2', text)

        # STEP 3: Handle existing single \n (upgrade to \n\n)
        text = re.sub(r'(\*\*[^*]+\*\*)\n([A-Za-z0-9"\'\(\[`])', r'\1\n\n\2', text)
        text = re.sub(r'([.?!:;,\)\]\'\"\*])\n(\*\*[A-Z])', r'\1\n\n\2', text)

        # Cleanup: collapse triple+ newlines to double
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')

    if '__' in text:
        text = re.sub(r'__\s+', '__', text)
        text = re.sub(r'\s+__', '__', text)
        text = re.sub(r'(__.+?__)[ \t]*([A-Za-z0-9"\'\(\[`])', r'\1\n\n\2', text)
        text = re.sub(r'([.?!:;,\)\]\'\"\*])[ \t]*(__[A-Z])', r'\1\n\n\2', text)
        text = re.sub(r'(__.+?__)\n([A-Za-z0-9"\'\(\[`])', r'\1\n\n\2', text)
        text = re.sub(r'([.?!:;,\)\]\'\"\*])\n(__[A-Z])', r'\1\n\n\2', text)
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')

    return text
