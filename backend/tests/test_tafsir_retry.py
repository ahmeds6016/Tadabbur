"""Offline route tests: execute app functions without credential/startup side effects."""

import ast
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
import re
import threading
import time
import traceback
from types import SimpleNamespace
from typing import Any, Dict, Optional
from unittest.mock import Mock

from flask import Flask, g, jsonify, make_response, request
import pytest
import requests


MALFORMED = "An error occurred while evaluating the response."
VALID = json.dumps({"verses": [], "tafsir_explanations": [], "metadata": {}})


def gemini_response(text, status=200, finish_reason="STOP"):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps({
        "candidates": [{"content": {"parts": [{"text": text}]},
                        "finishReason": finish_reason}],
        "usageMetadata": {"candidatesTokenCount": 12},
    }).encode()
    return response


@pytest.fixture
def route_env(monkeypatch):
    # Compile the actual full handlers and parsing helpers, not copies. Importing
    # app.py would initialize cloud clients and read local credentials/corpora.
    path = Path(__file__).resolve().parents[1] / "app.py"
    names = {
        "tafsir_handler_enhanced", "debug_query", "extract_json_from_response",
        "fix_malformed_json", "extract_gemini_text", "safe_get_nested", "_single_line_log",
    }
    functions = [node for node in ast.parse(path.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in functions} == names
    for node in functions:
        node.decorator_list = []

    post = Mock()
    sleep = Mock()
    store = Mock()
    credentials = Mock(token="offline-token")
    fake_google = SimpleNamespace(auth=SimpleNamespace(
        default=Mock(return_value=(credentials, None)),
        transport=SimpleNamespace(requests=SimpleNamespace(Request=Mock())),
    ))
    verse = {"surah_number": 2, "verse_number": 255, "surah_name": "Al-Baqarah"}
    namespace = {
        "Any": Any, "Dict": Dict, "Optional": Optional,
        "datetime": datetime, "hashlib": hashlib, "json": json, "re": re,
        "traceback": traceback, "logger": logging.getLogger("tafsir_retry_test"),
        "time": SimpleNamespace(time=time.time, sleep=sleep),
        "g": g, "request": request, "jsonify": jsonify, "make_response": make_response,
        "requests": SimpleNamespace(post=post, Timeout=requests.Timeout,
                                    HTTPError=requests.HTTPError, exceptions=requests.exceptions),
        "google": fake_google, "GoogleRequest": Mock(),
        "GEMINI_MODEL_ID": "offline-model", "vertex_generate_url": lambda _: "https://offline.invalid",
        "RESPONSE_CACHE": {}, "cache_lock": threading.Lock(), "ANALYTICS": defaultdict(int),
        "QURAN_METADATA": {2: {"verses": 286}},
        "extract_verse_reference_enhanced": lambda _: (2, 255),
        "extract_verse_range": lambda _: None,
        "classify_query_enhanced": lambda _: {"verse_ref": (2, 255), "confidence": 1},
        "validate_verse_reference": lambda *args: (True, ""),
        "is_rate_limited": lambda *args, **kwargs: False,
        "get_cache_key": lambda *args: "fixture-cache-key",
        "get_cached_tafsir_response": lambda *args: None,
        "get_verse_from_firestore": lambda *args: verse,
        "get_verse_metadata_direct": lambda *args, **kwargs: [
            {"source": "Ibn Kathir", "metadata": {"commentary": "Fixture commentary"}}],
        "get_arabic_text_from_verse_data": lambda _: "Fixture Arabic",
        "_get_scholarly_context_two_stage": lambda *args: ("", [], {}, {}),
        "build_structured_context": lambda *args: "Fixture source context",
        "build_enhanced_prompt": lambda *args, **kwargs: "Fixture prompt",
        "validate_hadith_items": lambda *args: ([], []),
        "filter_unavailable_sources": lambda value: value,
        "keep_requested_verses_primary": lambda value, *args, **kwargs: value,
        "enforce_persona_verse_limit": lambda value, *args, **kwargs: (value, False, 0, 0),
        "_generate_recommendations": lambda *args: [],
        "store_tafsir_cache": store,
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)

    monkeypatch.syspath_prepend(str(path.parent))
    import services.token_budget_service as budget
    monkeypatch.setattr(budget, "compute_max_end_verse", lambda *args: (255, {}))
    app = Flask(__name__)

    @app.before_request
    def guest_request():
        request.user = None
        g.request_started_at = time.time()

    app.add_url_rule("/tafsir", view_func=namespace["tafsir_handler_enhanced"], methods=["POST"])
    app.add_url_rule("/debug/test/<path:query>", view_func=namespace["debug_query"])
    return SimpleNamespace(client=app.test_client(), post=post, sleep=sleep,
                           store=store, cache=namespace["RESPONSE_CACHE"])


def assert_attempt_budget(env, attempts):
    assert env.post.call_count == attempts
    timeouts = [call.kwargs["timeout"] for call in env.post.call_args_list]
    assert timeouts == [120] * attempts
    assert sum(timeouts) + sum(call.args[0] for call in env.sleep.call_args_list) <= 242


def test_malformed_then_valid_retries_logs_and_caches(route_env, caplog):
    env = route_env
    env.post.side_effect = [gemini_response(MALFORMED), gemini_response(VALID)]
    with caplog.at_level(logging.INFO):
        response = env.client.post("/tafsir", json={"query": "2:255"})
    assert response.status_code == 200
    assert_attempt_budget(env, 2)
    assert caplog.messages.count("GEMINI_RETRY_MALFORMED verse=2:255") == 1
    assert sum(message.startswith("GEMINI_USAGE ") for message in caplog.messages) == 2
    env.store.assert_called_once()
    assert env.store.call_args.args[2] == response.get_json()
    assert env.cache == {"fixture-cache-key": response.get_json()}
    assert not response.get_json()["metadata"].get("extraction_error")


def test_malformed_twice_returns_502_without_caching(route_env, caplog):
    env = route_env
    env.post.side_effect = [gemini_response(MALFORMED), gemini_response(MALFORMED)]
    response = env.client.post("/tafsir", json={"query": "2:255"})
    assert response.status_code == 502
    assert response.get_json() == {"error": "AI returned a malformed response. Please try again."}
    assert_attempt_budget(env, 2)
    assert caplog.messages.count("GEMINI_RETRY_MALFORMED verse=2:255") == 1
    env.store.assert_not_called()
    assert env.cache == {}


@pytest.mark.parametrize("failure", ["timeout", 429, 503])
@pytest.mark.parametrize("second_text", [MALFORMED, VALID])
def test_network_retry_consumes_same_slot(route_env, caplog, failure, second_text):
    env = route_env
    first = requests.Timeout() if failure == "timeout" else gemini_response("", failure)
    env.post.side_effect = [first, gemini_response(second_text)]
    response = env.client.post("/tafsir", json={"query": "2:255"})
    assert response.status_code == (502 if second_text == MALFORMED else 200)
    assert_attempt_budget(env, 2)
    env.sleep.assert_called_once_with(2)
    assert "GEMINI_RETRY_MALFORMED verse=2:255" not in caplog.messages
    assert env.store.call_count == (0 if second_text == MALFORMED else 1)
    assert bool(env.cache) == (second_text == VALID)


@pytest.mark.parametrize("failure, expected_status", [("timeout", 503), (429, 429), (503, 500)])
def test_network_failure_after_malformed_does_not_get_third_attempt(route_env, failure, expected_status):
    env = route_env
    second = requests.Timeout() if failure == "timeout" else gemini_response("", failure)
    env.post.side_effect = [gemini_response(MALFORMED), second]
    response = env.client.post("/tafsir", json={"query": "2:255"})
    assert response.status_code == expected_status
    assert_attempt_budget(env, 2)
    env.store.assert_not_called()
    assert env.cache == {}


def test_valid_first_response_needs_one_call(route_env):
    env = route_env
    env.post.side_effect = [gemini_response(VALID)]
    response = env.client.post("/tafsir", json={"query": "2:255"})
    assert response.status_code == 200
    assert_attempt_budget(env, 1)
    env.store.assert_called_once()


def test_safety_response_is_not_retried_or_cached(route_env):
    env = route_env
    env.post.side_effect = [gemini_response(MALFORMED, finish_reason="SAFETY")]
    response = env.client.post("/tafsir", json={"query": "2:255"})
    assert response.status_code == 400
    assert_attempt_budget(env, 1)
    env.store.assert_not_called()
    assert env.cache == {}


def test_debug_handler_still_makes_single_attempt(route_env, caplog):
    env = route_env
    env.post.side_effect = [gemini_response(MALFORMED)]
    response = env.client.get("/debug/test/2:255")
    assert response.status_code == 500
    assert response.get_json()["error"] == "Failed to parse AI response"
    assert_attempt_budget(env, 1)
    assert "GEMINI_RETRY_MALFORMED verse=2:255" not in caplog.messages
    env.store.assert_not_called()
    assert env.cache == {}
