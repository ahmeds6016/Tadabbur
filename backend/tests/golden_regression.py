#!/usr/bin/env python3
"""Live golden regression harness for a Tadabbur Cloud Run revision.

Claude's model-flip procedure:
1. Run this script against the current production URL to capture a baseline.
2. Deploy a NO-TRAFFIC canary revision with
   GEMINI_MODEL_ID=gemini-3.6-flash and
   GEMINI_LITE_MODEL_ID=gemini-3.5-flash-lite.
3. Run this script against the canary URL, supplying a preconfigured bearer token
   for each persona, and compare its timestamped raw output with the baseline.
4. Review both structural failures and content diffs before shifting any traffic.
5. Shift traffic only after approval; bump the pipeline version if generated
   content shifts materially.

This is a script, not a pytest test. It makes 12 paid /tafsir requests and should
never be pointed at production casually. The current backend derives an authenticated
persona from that user's saved profile and forces unauthenticated calls to the guest
default, so true persona comparison requires --persona-token for both personas.

Example:
  python tests/golden_regression.py --base-url https://CANARY_URL \
    --persona-token curious_explorer=TOKEN_ONE --persona-token student=TOKEN_TWO
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.hadith_validation import validate_hadith_items


PERSONAS = ("curious_explorer", "student")
REQUIRED_KEYS = {
    "verses",
    "tafsir_explanations",
    "lessons_practical_applications",
    "summary",
    "reflection_prompt",
    "source_coverage",
}
GENERIC_REFLECTION_PHRASES = (
    "how does this verse apply to your life",
    "what can you learn from this verse",
    "reflect on this verse",
    "what does this verse mean to you",
)
VERSE_CASES = (
    {
        "query": "1:5",
        "label": "worship and reliance",
        "reflection_tokens": {"worship", "help", "rely", "depend", "alone"},
    },
    {
        "query": "2:255",
        "label": "Ayat al-Kursi",
        "reflection_tokens": {
            "ever-living", "sustainer", "slumber", "throne", "knowledge", "intercession"
        },
    },
    {
        "query": "4:23",
        "label": "post-al-Qurtubi coverage boundary",
        "reflection_tokens": {"mother", "daughter", "sister", "marriage", "kinship", "forbidden"},
    },
    {
        "query": "6:57",
        "label": "deterministic-only scholarly plan",
        "reflection_tokens": {"judgment", "decision", "truth", "authority", "decide"},
    },
    {
        "query": "93:3",
        "label": "grief and reassurance",
        "reflection_tokens": {"forsaken", "abandoned", "lord", "comfort", "left"},
    },
    {
        "query": "112:1-4",
        "label": "divine oneness range",
        "reflection_tokens": {"oneness", "eternal", "begotten", "comparable", "equivalent", "depend"},
    },
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run Tadabbur's live structural and grounding canary checks."
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL of the production baseline or no-traffic canary revision.",
    )
    parser.add_argument(
        "--persona-token",
        action="append",
        default=[],
        metavar="PERSONA=TOKEN",
        help=(
            "Bearer token for a user whose saved profile matches PERSONA. Repeat for "
            "curious_explorer and student for a true comparison."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "golden-results"),
        help="Parent directory for timestamped raw response folders.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Per-request timeout in seconds (default: 300).",
    )
    return parser.parse_args(argv)


def parse_persona_tokens(values):
    tokens = {}
    for value in values:
        persona, separator, token = value.partition("=")
        if not separator or persona not in PERSONAS or not token.strip():
            raise ValueError(
                "--persona-token must be curious_explorer=TOKEN or student=TOKEN"
            )
        tokens[persona] = token.strip()
    return tokens


def iter_nonempty_text(value):
    """Yield non-empty textual fields from a decoded response."""
    if isinstance(value, str):
        if value.strip():
            yield value.strip()
    elif isinstance(value, dict):
        for nested in value.values():
            yield from iter_nonempty_text(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_nonempty_text(nested)


def validate_response(payload, headers, case):
    failures = []
    missing = sorted(REQUIRED_KEYS - set(payload))
    if missing:
        failures.append(f"missing keys: {', '.join(missing)}")

    explanations = payload.get("tafsir_explanations")
    if not isinstance(explanations, list) or not explanations:
        failures.append("tafsir_explanations is empty or not a list")

    lessons = payload.get("lessons_practical_applications")
    if not isinstance(lessons, list) or len(lessons) != 3:
        count = len(lessons) if isinstance(lessons, list) else "not-a-list"
        failures.append(f"expected exactly 3 lessons, got {count}")

    coverage = payload.get("source_coverage")
    if not isinstance(coverage, dict) or not coverage:
        failures.append("source_coverage is absent or empty")

    if not headers.get("X-Cache-Status"):
        failures.append("X-Cache-Status header is absent")

    reflection = payload.get("reflection_prompt", "")
    normalized_reflection = re.sub(r"\s+", " ", str(reflection)).strip().casefold()
    if len(normalized_reflection) < 60:
        failures.append("reflection_prompt is shorter than 60 characters")
    if any(phrase in normalized_reflection for phrase in GENERIC_REFLECTION_PHRASES):
        failures.append("reflection_prompt contains a generic reflection phrase")
    if not any(token in normalized_reflection for token in case["reflection_tokens"]):
        failures.append("reflection_prompt lacks a verse-linked token")

    hadith = payload.get("hadith", [])
    if not isinstance(hadith, list):
        failures.append("hadith is not a list")
    else:
        nonempty_context = "\n".join(iter_nonempty_text(payload))
        kept, dropped = validate_hadith_items(hadith, nonempty_context)
        if dropped or len(kept) != len(hadith):
            reasons = sorted({item.get("_validation_reason", "unknown") for item in dropped})
            failures.append(
                "hadith validator rejected response item(s): " + ", ".join(reasons)
            )

    return failures


def run_case(session, base_url, persona, token, case, timeout, raw_path):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request_body = {
        "query": case["query"],
        "approach": "tafsir",
        "persona": persona,
    }

    started = time.monotonic()
    envelope = {
        "request": request_body,
        "requested_persona": persona,
    }
    try:
        response = session.post(
            f"{base_url}/tafsir",
            headers=headers,
            json=request_body,
            timeout=timeout,
        )
        duration = time.monotonic() - started
        envelope.update({
            "status_code": response.status_code,
            "response_headers": dict(response.headers),
            "elapsed_seconds": round(duration, 3),
        })
        try:
            payload = response.json()
            envelope["response_json"] = payload
        except ValueError:
            payload = None
            envelope["response_text"] = response.text

        raw_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")

        failures = []
        if response.status_code < 200 or response.status_code >= 300:
            failures.append(f"HTTP {response.status_code}")
        if payload is None:
            failures.append("response is not valid JSON")
        elif not isinstance(payload, dict):
            failures.append("JSON response is not an object")
        else:
            failures.extend(validate_response(payload, response.headers, case))

        return {
            "query": case["query"],
            "persona": persona,
            "status": "PASS" if not failures else "FAIL",
            "cache": response.headers.get("X-Cache-Status", "—"),
            "seconds": f"{duration:.1f}",
            "details": "; ".join(failures) if failures else "all invariants",
        }
    except requests.RequestException as exc:
        duration = time.monotonic() - started
        envelope.update({
            "elapsed_seconds": round(duration, 3),
            "request_error": f"{type(exc).__name__}: {exc}",
        })
        raw_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "query": case["query"],
            "persona": persona,
            "status": "FAIL",
            "cache": "—",
            "seconds": f"{duration:.1f}",
            "details": f"{type(exc).__name__}: {exc}",
        }


def print_table(results):
    columns = ("query", "persona", "status", "cache", "seconds", "details")
    widths = {
        column: max(len(column), *(len(str(result[column])) for result in results))
        for column in columns
    }
    header = " | ".join(column.upper().ljust(widths[column]) for column in columns)
    divider = "-+-".join("-" * widths[column] for column in columns)
    print(header)
    print(divider)
    for result in results:
        print(" | ".join(str(result[column]).ljust(widths[column]) for column in columns))


def main(argv=None):
    args = parse_args(argv)
    try:
        persona_tokens = parse_persona_tokens(args.persona_token)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    missing_tokens = [persona for persona in PERSONAS if persona not in persona_tokens]
    if missing_tokens:
        print(
            "WARNING: true persona comparison requires configured --persona-token values "
            f"for: {', '.join(missing_tokens)}. Missing cases will use the guest default profile.",
            file=sys.stderr,
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.output_dir).expanduser().resolve() / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)
    base_url = args.base_url.rstrip("/")

    results = []
    with requests.Session() as session:
        case_number = 0
        for persona in PERSONAS:
            for case in VERSE_CASES:
                case_number += 1
                safe_query = case["query"].replace(":", "-")
                raw_path = run_dir / f"{case_number:02d}_{safe_query}_{persona}.json"
                result = run_case(
                    session,
                    base_url,
                    persona,
                    persona_tokens.get(persona),
                    case,
                    args.timeout,
                    raw_path,
                )
                results.append(result)
                print(f"[{case_number:02d}/12] {result['status']} {case['query']} / {persona}")

    print()
    print_table(results)
    print(f"\nRaw responses: {run_dir}")
    failures = sum(result["status"] == "FAIL" for result in results)
    print(f"Result: {len(results) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
