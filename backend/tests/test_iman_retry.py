"""Offline tests of the real Iman handlers' HTTP retry branches."""

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask, jsonify, request as flask_request
import google.auth
import pytest
import requests

from backend.tests.test_tafsir_retry import gemini_response


class Monday(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 14, tzinfo=tz)


@pytest.fixture(params=["iman_generate_digest", "iman_get_daily_insight"])
def iman_route(request, monkeypatch):
    name = request.param
    path = Path(__file__).resolve().parents[1] / "app.py"
    handler = next(node for node in ast.parse(path.read_text()).body
                   if isinstance(node, ast.FunctionDef) and node.name == name)
    handler.decorator_list = []
    writes = Mock()

    class FakeDB:
        def __init__(self, collection_name="users"):
            self.collection_name = collection_name

        def collection(self, name):
            return FakeDB(name)

        def document(self, *args):
            return self

        def get(self):
            return SimpleNamespace(exists=self.collection_name == "iman_daily_logs",
                                   to_dict=lambda: {"date": "2026-09-14"})

        def where(self, *args, **kwargs):
            return self

        order_by = where
        limit = where

        def stream(self):
            return [self.get()] * 4 if self.collection_name == "iman_daily_logs" else []

        def set(self, value):
            writes(value)

    monkeypatch.setattr(google.auth, "default", Mock(return_value=(Mock(token="offline"), None)))
    post, sleep = Mock(), Mock()
    namespace = {
        "datetime": Monday, "timedelta": timedelta, "timezone": timezone,
        "request": flask_request, "jsonify": jsonify, "users_db": FakeDB(),
        "firestore": SimpleNamespace(Query=SimpleNamespace(DESCENDING="DESCENDING")),
        "STRUGGLE_MAP": {}, "build_default_config": lambda: {},
        "prepare_digest_context": lambda *args, **kwargs: {"days_logged_this_week": 4, "trajectory_state": "steady"},
        "prepare_daily_insight_context": lambda *args, **kwargs: {},
        "build_digest_prompt": lambda *args: "offline",
        "build_daily_insight_prompt": lambda *args: "offline",
        "vertex_generate_url": lambda _: "https://offline.invalid", "GEMINI_MODEL_ID": "offline",
        "requests": SimpleNamespace(post=post, Timeout=requests.Timeout, HTTPError=requests.HTTPError),
        "time": SimpleNamespace(sleep=sleep),
        "extract_gemini_text": lambda data: "valid",
        "extract_json_from_response": lambda text: {"opening": "fixture", "observation": "fixture"},
        "_encrypt_text": lambda text, uid: text,
    }
    exec(compile(ast.Module(body=[handler], type_ignores=[]), str(path), "exec"), namespace)
    app = Flask(__name__)

    @app.before_request
    def authenticate():
        flask_request.user = {"uid": "offline-user"}

    with app.test_request_context("/", method="POST", json={}):
        authenticate()
        def call():
            args = ["2026-09-14"] if name == "iman_get_daily_insight" else []
            return namespace[name](*args)
        yield SimpleNamespace(call=call, post=post, sleep=sleep, writes=writes)


def test_429_then_success_retries_once(iman_route):
    env = iman_route
    first = gemini_response("", 429)
    assert not first  # Use requests.Response's real falsey error behavior.
    env.post.side_effect = [first, gemini_response("valid")]
    response, status = env.call()
    assert status == 200
    assert response.get_json()["cached"] is False
    assert env.post.call_count == 2
    env.sleep.assert_called_once_with(2)
    env.writes.assert_called_once()


def test_503_on_last_attempt_raises_http_error_and_stops(iman_route):
    env = iman_route
    last = gemini_response("", 503)
    last.raise_for_status = Mock(wraps=last.raise_for_status)
    env.post.side_effect = [gemini_response("", 429), gemini_response("", 503), last]
    response, status = env.call()
    # The existing handler catches the raised HTTPError and returns 502.
    assert status == 502
    assert response.get_json() == {"error": "AI service error"}
    last.raise_for_status.assert_called_once()
    assert env.post.call_count == 3
    assert [call.args[0] for call in env.sleep.call_args_list] == [2, 4]
    env.writes.assert_not_called()
