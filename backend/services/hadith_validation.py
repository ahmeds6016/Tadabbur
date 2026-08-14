"""Pure validation helpers for source-grounded hadith response items."""

import re
import unicodedata
from collections import Counter


SHINGLE_SIZE = 12
MIN_SHINGLE_MATCH_RATIO = 0.80
MIN_SHORT_ITEM_WORDS = 4
COLLECTION_CONTEXT_WORDS = 24

_GENERIC_COLLECTION_WORDS = {
    "al", "book", "collection", "jami", "jamiu", "musnad", "sahih", "sunan", "the",
}

_KNOWN_COLLECTION_PATTERNS = (
    (re.compile(r"\bsahih\s+(?:al\s+)?bukhari\b", re.IGNORECASE), "Sahih al-Bukhari"),
    (re.compile(r"\bsahih\s+muslim\b", re.IGNORECASE), "Sahih Muslim"),
    (re.compile(r"\b(?:musnad\s+)?ahmad\b", re.IGNORECASE), "Musnad Ahmad"),
    (re.compile(r"\b(?:jami\s+)?(?:al\s+)?tirmidhi\b", re.IGNORECASE), "Jami al-Tirmidhi"),
    (re.compile(r"\bsunan\s+(?:abi\s+)?dawud\b", re.IGNORECASE), "Sunan Abi Dawud"),
    (re.compile(r"\bsunan\s+(?:al\s+)?nasai\b", re.IGNORECASE), "Sunan al-Nasa'i"),
    (re.compile(r"\bsunan\s+ibn\s+majah\b", re.IGNORECASE), "Sunan Ibn Majah"),
    (re.compile(r"\briyad\s+(?:al\s+)?saliheen\b", re.IGNORECASE), "Riyad al-Saliheen"),
)


def _normalize_tokens(value):
    """Lowercase text and remove punctuation, diacritics, and repeated whitespace."""
    if value is None:
        return []
    normalized = unicodedata.normalize("NFKD", str(value)).casefold()
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = "".join(ch if ch.isalnum() else " " for ch in normalized)
    return normalized.split()


def _infer_collection(reference):
    if not isinstance(reference, str):
        return ""
    for pattern, collection in _KNOWN_COLLECTION_PATTERNS:
        if pattern.search(reference):
            return collection
    return ""


def _reference_parts(item):
    reference = item.get("reference", "")
    if isinstance(reference, dict):
        collection = reference.get("collection") or item.get("collection") or ""
        narrator = reference.get("narrator") or item.get("narrator") or ""
        attribution = reference.get("attribution") or item.get("attribution") or ""
    else:
        collection = item.get("collection") or _infer_collection(reference)
        narrator = item.get("narrator") or ""
        attribution = item.get("attribution") or ""

    collection = str(collection).strip() if collection else ""
    narrator = str(narrator).strip() if narrator else ""
    attribution = str(attribution).strip() if attribution else ""
    if collection.casefold() in {"none", "null", "not provided", "unknown"}:
        collection = ""
    return collection, narrator, attribution


def _text_match(item_tokens, source_tokens):
    """Return (matched, aligned source start, ratio) for a hadith item.

    Items of at least 12 words are split into overlapping 12-word shingles. At
    least 80% of those exact normalized shingles must occur in the supplied
    source context. Shorter items must occur as one exact 4+-word token sequence.
    The conservative threshold favors dropping an item over presenting wording
    that the supplied sources do not support.
    """
    if len(item_tokens) < MIN_SHORT_ITEM_WORDS or not source_tokens:
        return False, None, 0.0

    if len(item_tokens) < SHINGLE_SIZE:
        width = len(item_tokens)
        needle = tuple(item_tokens)
        for start in range(len(source_tokens) - width + 1):
            if tuple(source_tokens[start:start + width]) == needle:
                return True, start, 1.0
        return False, None, 0.0

    source_shingles = {}
    for start in range(len(source_tokens) - SHINGLE_SIZE + 1):
        shingle = tuple(source_tokens[start:start + SHINGLE_SIZE])
        source_shingles.setdefault(shingle, []).append(start)

    total = len(item_tokens) - SHINGLE_SIZE + 1
    matched = 0
    alignments = []
    for item_start in range(total):
        shingle = tuple(item_tokens[item_start:item_start + SHINGLE_SIZE])
        source_starts = source_shingles.get(shingle, [])
        if source_starts:
            matched += 1
            alignments.extend(source_start - item_start for source_start in source_starts)

    ratio = matched / total
    if ratio < MIN_SHINGLE_MATCH_RATIO or not alignments:
        return False, None, ratio

    aligned_start = Counter(alignments).most_common(1)[0][0]
    return True, max(0, aligned_start), ratio


def _collection_is_supported(collection, source_tokens, matched_start):
    """Require a named collection immediately before the matching wording.

    This deliberately does not accept a collection mentioned only after a quote:
    source discussions often say that another collection *omits* the preceding
    wording. Requiring a preceding attribution prevents that pattern from turning
    an Ahmad wording into a Muslim wording, at the cost of safely dropping some
    ambiguous citations.
    """
    if not collection:
        return True

    collection_tokens = [
        token for token in _normalize_tokens(collection)
        if token not in _GENERIC_COLLECTION_WORDS
    ]
    if not collection_tokens or matched_start is None:
        return False

    window_start = max(0, matched_start - COLLECTION_CONTEXT_WORDS)
    attribution_window = source_tokens[window_start:matched_start]
    return all(token in attribution_window for token in collection_tokens)


def _display_reference(collection, narrator, attribution):
    parts = []
    if collection:
        parts.append(collection)
    if narrator:
        narrator_display = narrator
        if not narrator.casefold().startswith(("narrated by", "narrator:")):
            narrator_display = f"narrated by {narrator}"
        parts.append(narrator_display)
    if attribution:
        parts.append(attribution)
    if not parts:
        parts.append("As cited in the supplied source excerpts")
    return "; ".join(parts)


def validate_hadith_items(hadith_list, source_context_text):
    """Validate and normalize generated hadith items against prompt sources.

    Returns ``(kept, dropped)``. Kept items retain the frontend's display-string
    ``reference`` and add ``collection``, ``narrator``, and ``attribution`` fields.
    Dropped item copies include a private ``_validation_reason`` for server logs;
    callers must not return them to clients. Kept items whose verified wording
    could not be tied to the claimed collection carry the stripped label in a
    private ``_downgraded_collection`` key — callers should log and pop it
    before caching or serving.
    """
    if not hadith_list:
        return [], []
    if not isinstance(hadith_list, list):
        return [], [{
            "reference": "Invalid hadith collection",
            "_validation_reason": "hadith_not_list",
        }]

    source_tokens = _normalize_tokens(source_context_text)
    kept = []
    dropped = []

    for raw_item in hadith_list:
        if not isinstance(raw_item, dict):
            dropped.append({
                "reference": "Invalid non-object hadith item",
                "_validation_reason": "item_not_object",
            })
            continue

        item = dict(raw_item)
        item_tokens = _normalize_tokens(item.get("text", ""))
        matched, matched_start, match_ratio = _text_match(item_tokens, source_tokens)
        if not matched:
            item["_validation_reason"] = f"source_text_match={match_ratio:.2f}"
            dropped.append(item)
            continue

        collection, narrator, attribution = _reference_parts(item)
        if collection and not _collection_is_supported(collection, source_tokens, matched_start):
            # The wording itself is verified verbatim against the supplied
            # sources — only the collection label could not be tied to this
            # wording. Keep the hadith but strip the unverified label rather
            # than losing grounded content (downgrade, not drop).
            item["_downgraded_collection"] = collection
            collection = ""

        if not attribution:
            attribution = "As cited in the supplied source excerpts"

        item["collection"] = collection
        item["narrator"] = narrator
        item["attribution"] = attribution
        item["reference"] = _display_reference(collection, narrator, attribution)
        item.setdefault("text", "")
        item.setdefault("relevance", "")
        kept.append(item)

    return kept, dropped
