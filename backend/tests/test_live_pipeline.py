"""
LIVE integration test: Full A-to-Z two-stage scholarly pipeline.
Makes real Gemini API calls — requires GCP credentials.

Usage:
  python backend/tests/test_live_pipeline.py
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import google.auth
from google.auth.transport.requests import Request as GoogleRequest
import requests

from services.source_service import (
    build_scholarly_planning_prompt,
    resolve_scholarly_pointers,
    format_scholarly_excerpts_for_prompt,
    MAX_TOTAL_SCHOLARLY_CHARS,
)

# --- Config (mirrors app.py) ---
GCP_PROJECT = os.environ.get("GCP_INFRASTRUCTURE_PROJECT", "tafsir-simplified")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
MODEL = os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash")


def safe_get_nested(data, *keys, default=None):
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return default
    return current


def call_gemini_planning(prompt):
    """Make real Gemini planning call."""
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = GoogleRequest()
    credentials.refresh(auth_req)

    endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent"

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generation_config": {
            "response_mime_type": "application/json",
            "temperature": 0.05,
            "top_k": 10,
            "top_p": 0.8,
            "maxOutputTokens": 8192,
        },
    }

    start = time.time()
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"},
        json=body,
        timeout=35,
    )
    duration = time.time() - start
    response.raise_for_status()

    raw = response.json()
    text = safe_get_nested(raw, "candidates", 0, "content", "parts", 0, "text")
    if not text:
        print(f"  RAW RESPONSE: {json.dumps(raw, indent=2)[:2000]}")
        raise ValueError("Empty response from Gemini")
    try:
        return json.loads(text), duration
    except json.JSONDecodeError as e:
        print(f"  RAW TEXT from Gemini ({len(text)} chars):")
        print(f"  ---BEGIN---")
        print(text)
        print(f"  ---END---")
        print(f"  Finish reason: {safe_get_nested(raw, 'candidates', 0, 'finishReason')}")
        # Try to fix common issues: extract JSON from markdown fences
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group()), duration
        raise


def run_test(label, surah, verse_start, verse_end, verse_text, ik_summary, query):
    """Run one full pipeline test."""
    print(f"\n{'='*70}")
    print(f"TEST: {label}")
    print(f"{'='*70}")

    # Stage 1: Build planning prompt
    prompt = build_scholarly_planning_prompt(surah, verse_start, verse_end, verse_text, ik_summary, query)
    print(f"  Planning prompt: {len(prompt)} chars")

    # Stage 2: Call Gemini
    plan, duration = call_gemini_planning(prompt)
    pointers = plan.get("pointers", [])
    reasoning = plan.get("reasoning", "")
    print(f"  Gemini response: {duration:.2f}s")
    print(f"  Pointers ({len(pointers)}):")
    for p in pointers:
        print(f"    - {p}")
    print(f"  Reasoning: {reasoning}")

    # Validate pointer formats
    for p in pointers:
        parts = p.split(":")
        assert len(parts) >= 2, f"Bad pointer format: {p}"
        assert parts[0] in ("asbab", "thematic", "ihya", "madarij", "riyad"), f"Unknown source: {parts[0]}"
        for part in parts[1:]:
            assert "=" in part, f"Missing = in pointer segment: {part} (full: {p})"
    print(f"  Format validation: PASS")

    # Check mandatory pointers
    asbab_ptr = f"asbab:surah={surah}:verse={verse_start}"
    thematic_ptr = f"thematic:surah={surah}:section=0"
    assert any(asbab_ptr in p for p in pointers), f"Missing mandatory: {asbab_ptr}"
    assert any(thematic_ptr in p for p in pointers), f"Missing mandatory: {thematic_ptr}"
    print(f"  Mandatory pointers (asbab + thematic): PASS")

    # Stage 3: Resolve pointers
    resolved = resolve_scholarly_pointers(pointers)
    excerpts = resolved["excerpts"]
    badges = resolved["sources_used"]
    total_chars = sum(len(e["text"]) for e in excerpts)

    print(f"  Resolved: {len(excerpts)} excerpts, {total_chars} chars, {len(badges)} badges")
    for e in excerpts:
        print(f"    - [{e['source_id']}] {e['title'][:60]}... ({len(e['text'])} chars)")

    # Verify char budget
    assert total_chars <= MAX_TOTAL_SCHOLARLY_CHARS + 10, f"Over budget: {total_chars}"
    print(f"  Char budget: PASS ({total_chars}/{MAX_TOTAL_SCHOLARLY_CHARS})")

    # Verify badges match resolved sources
    badge_keys = {b["key"] for b in badges}
    excerpt_ids = {e["source_id"] for e in excerpts}
    assert badge_keys == excerpt_ids, f"Badge mismatch: badges={badge_keys}, excerpts={excerpt_ids}"
    print(f"  Badge accuracy: PASS")

    # Stage 4: Format for generation prompt
    formatted = format_scholarly_excerpts_for_prompt(resolved)
    assert "CRITICAL INSTRUCTIONS" in formatted
    assert "EXCERPT 1" in formatted
    print(f"  Formatted prompt: {len(formatted)} chars")
    print(f"  RESULT: ALL CHECKS PASSED")

    return {
        "label": label,
        "pointers": pointers,
        "excerpts_count": len(excerpts),
        "total_chars": total_chars,
        "badges": [b["key"] for b in badges],
        "duration": duration,
    }


if __name__ == "__main__":
    results = []

    # Test 1: Rich verse (mercy, forgiveness, repentance, hope)
    results.append(run_test(
        "39:53 — Mercy/Hope/Repentance (expect 4-6 pointers, 3+ sources)",
        39, 53, 53,
        "Say, O My servants who have transgressed against themselves, do not despair of the mercy of Allah. Indeed, Allah forgives all sins.",
        "mercy forgiveness repentance hope despair tawbah Allah's mercy encompasses all sinners",
        "Explain Surah 39 verse 53"
    ))

    # Test 2: Narrative verse (expect only 2 pointers)
    results.append(run_test(
        "12:80 — Yusuf narrative (expect 2 pointers, asbab + thematic only)",
        12, 80, 80,
        "So when they had despaired of him, they secluded themselves in private consultation.",
        "Yusuf brothers despair consultation oath to father Jacob Benjamin",
        "Explain the story in 12:80"
    ))

    # Test 3: Death-related verse
    results.append(run_test(
        "33:16 — Death/Fleeing (expect 3 pointers, death match to Ihya)",
        33, 16, 16,
        "Say, Never will fleeing benefit you if you should flee from death or killing.",
        "death fleeing battle hypocrisy divine decree cowardice",
        "Explain 33:16"
    ))

    # Test 4: Patience verse
    results.append(run_test(
        "2:153 — Patience (expect 5+ pointers across Ihya/Madarij/Riyad)",
        2, 153, 153,
        "O you who have believed, seek help through patience and prayer. Indeed, Allah is with the patient.",
        "patience sabr prayer steadfastness believers",
        "What does 2:153 teach about patience?"
    ))

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for r in results:
        print(f"  {r['label']}")
        print(f"    Pointers: {len(r['pointers'])}, Excerpts: {r['excerpts_count']}, "
              f"Chars: {r['total_chars']}, Badges: {r['badges']}, API: {r['duration']:.2f}s")
    print(f"\nAll {len(results)} tests passed!")
