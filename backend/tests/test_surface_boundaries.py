"""Real request gates and counters with no startup/cloud clients."""
import ast
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import wraps
import hmac
import logging
import os
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock
import uuid
import sys

from flask import Flask, g, jsonify, make_response, request
import pytest
from werkzeug.middleware.proxy_fix import ProxyFix

SOURCE = Path(__file__).resolve().parents[1] / 'app.py'


@pytest.fixture
def surface():
    names = {'start_observed_request_timer', 'api_error', 'firebase_auth_required',
             'firebase_auth_optional', '_verify_admin_secret', 'admin_secret_required',
             'debug_route_required', 'is_rate_limited', 'record_query_analytics',
             'submit_feedback'}
    tree = ast.parse(SOURCE.read_text())
    app = Flask(__name__)
    ns = dict(sys=sys, VerseStoreUnavailable=type("VerseStoreUnavailable", (Exception,), {}), app=app, os=os, uuid=uuid, g=g, request=request, jsonify=jsonify,
              make_response=make_response, wraps=wraps, hmac=hmac, datetime=datetime,
              timedelta=timedelta, logger=logging.getLogger(__name__),
              ADMIN_SECRET='offline-admin', DEBUG_ROUTES_ENABLED=False,
              _account_is_deleting=lambda uid: False, auth=SimpleNamespace(verify_id_token=Mock(return_value={'uid': 'reader'})),
              rate_limit_lock=threading.RLock(), USER_RATE_LIMITS=defaultdict(list),
              COUNTER_MAX_KEYS=3, ANALYTICS=defaultdict(int), ANALYTICS_LAST_SEEN={})
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), ns)
    for route in ('lookup', 'analytics', 'popular'):
        # Keep the real decorator for each real operational route.
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and
                    any(isinstance(d, ast.Call) and d.args and isinstance(d.args[0], ast.Constant)
                        and d.args[0].value == f'/cache/{route}' for d in n.decorator_list))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), ns)
    return app, ns


def test_all_suspended_routes_fail_before_auth(surface, monkeypatch):
    app, ns = surface
    monkeypatch.delenv('IMAN_ENABLED', raising=False)
    routes = [d.args[0].value for n in ast.parse(SOURCE.read_text()).body
              if isinstance(n, ast.FunctionDef) for d in n.decorator_list
              if isinstance(d, ast.Call) and d.args and isinstance(d.args[0], ast.Constant)
              and str(d.args[0].value).startswith('/iman/')]
    assert len(routes) >= 28
    for route in routes:
        assert app.test_client().get(route).status_code == 404
    ns['auth'].verify_id_token.assert_not_called()


@pytest.mark.parametrize('path,method', [('/cache/lookup', 'post'), ('/cache/analytics', 'get'), ('/cache/popular', 'get')])
def test_cache_readers_are_admin_gated(surface, path, method):
    client = surface[0].test_client()
    assert getattr(client, method)(path).status_code == 403
    assert getattr(client, method)(path, headers={'X-Admin-Secret': 'wrong'}).status_code == 403


def test_feedback_has_required_auth_and_cheap_limit(surface):
    app, ns = surface
    assert app.test_client().post('/feedback', json={'message': 'Feedback'}).status_code == 401
    ns['is_rate_limited'] = Mock(return_value=True)
    response = app.test_client().post('/feedback', headers={'Authorization': 'Bearer offline'}, json={'message': 'Feedback'})
    assert response.status_code == 429
    assert response.headers['Retry-After'] == '3600'


def test_auth_exception_is_private_and_correlated(surface, caplog):
    app, ns = surface
    ns['auth'].verify_id_token.side_effect = RuntimeError('private-token-detail')
    response = app.test_client().post('/feedback', headers={'Authorization': 'Bearer offline'})
    assert response.status_code == 401
    assert 'private-token-detail' not in response.get_data(as_text=True)
    assert len(response.json['request_id']) == 12
    assert response.json['request_id'] in caplog.text


def test_counters_are_bounded_stale_and_atomic(surface):
    ns = surface[1]
    for i in range(10):
        ns['is_rate_limited'](str(i))
        ns['record_query_analytics'](str(i))
    assert len(ns['USER_RATE_LIMITS']) == len(ns['ANALYTICS']) == 3
    assert len(ns['ANALYTICS_LAST_SEEN']) == 3
    ns['USER_RATE_LIMITS']['old'] = [datetime.now() - timedelta(days=2)]
    ns['is_rate_limited']('new')
    assert 'old' not in ns['USER_RATE_LIMITS']
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(lambda _: ns['is_rate_limited']('same', limit=10), range(100)))
    assert outcomes.count(False) == 10


def test_one_proxy_hop_ignores_spoofed_prefix():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0)
    app.add_url_rule('/', view_func=lambda: jsonify({'ip': request.remote_addr}))
    response = app.test_client().get('/', headers={'X-Forwarded-For': 'spoofed, 198.51.100.6'})
    assert response.json['ip'] == '198.51.100.6'


def test_exception_strings_cannot_return_to_api_bodies():
    tree = ast.parse(SOURCE.read_text())
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
                isinstance(n.func, ast.Name) and n.func.id == 'str' and n.args and
                isinstance(n.args[0], ast.Name) and n.args[0].id == 'e']
