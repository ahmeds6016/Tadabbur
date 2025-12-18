import pytest

from utils.text_cleaning import sanitize_heading_format


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Sentence before. ## Heading After",
            "Sentence before.\n\n## Heading\n\nAfter"
        ),
        (
            "**Title**\nNext line",
            "## Title\n\nNext line"
        ),
        (
            "Line with no heading",
            "Line with no heading"
        ),
    ],
)
def test_sanitize_heading_format_blocks_headings(text, expected):
    assert sanitize_heading_format(text) == expected
