"""Offline Flask harness shared by topic tests and the manual smoke script."""

import ast
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
import json
import logging
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import Mock

from flask import Flask, jsonify, make_response, request
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.topic_service import (
    build_topic_index, topic_mapping_body, validate_topic_mapping, curated_topic_suggestions,
)


def make_topic_app():
    path = Path(__file__).resolve().parents[1] / "app.py"
    names = {"resolve_topics", "_map_topic_names", "extract_gemini_text", "safe_get_nested",
             "firebase_auth_optional", "is_rate_limited", "vertex_generate_url"}
    nodes = [node for node in ast.parse(path.read_text()).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    # Keep route and optional-auth decorators: exercise the actual registered route.
    app = Flask(__name__)
    post = Mock()
    clock = Mock(side_effect=time.monotonic)
    credentials = Mock(token="offline-token")
    namespace = {
        "app": app, "Any": Any, "Dict": Dict, "request": request, "jsonify": jsonify,
        "make_response": make_response, "wraps": wraps, "json": json,
        "datetime": datetime, "timedelta": timedelta,
        "logger": logging.getLogger("topic_test"), "time": SimpleNamespace(monotonic=clock),
        "auth": SimpleNamespace(verify_id_token=Mock(return_value={"uid": "offline-user"})),
        "google": SimpleNamespace(auth=SimpleNamespace(default=Mock(return_value=(credentials, None)))),
        "GoogleRequest": Mock(), "requests": SimpleNamespace(post=post),
        "GEMINI_LITE_MODEL_ID": "gemini-3.5-flash-lite", "GEMINI_API_LOCATION": "global",
        "GCP_INFRASTRUCTURE_PROJECT": "offline-project",
        "TOPIC_INDEX": build_topic_index(), "TOPIC_RESPONSE_CACHE": {},
        "TOPIC_CACHE_LOCK": threading.Lock(), "rate_limit_lock": threading.Lock(),
        "USER_RATE_LIMITS": defaultdict(list),
        "topic_mapping_body": topic_mapping_body,
        "validate_topic_mapping": validate_topic_mapping,
        "curated_topic_suggestions": curated_topic_suggestions,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return SimpleNamespace(client=app.test_client(), post=post, namespace=namespace, clock=clock)


def model_response(mapping):
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps({"candidates": [{"content": {"parts": [
        {"text": json.dumps(mapping)}]}}]}).encode()
    return response
