"""Real registered decorators/parser/cache/share code with fake clients only."""
import ast
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import wraps
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import sys
import threading
import time
import traceback
from types import SimpleNamespace
from unittest.mock import Mock
import uuid

from flask import Flask, g, has_request_context, jsonify, make_response, request
from flask_cors import CORS
import pytest
import requests

from backend.tests.test_content_boundaries import content
from backend.tests.test_tafsir_retry import VALID

PATH = Path(__file__).resolve().parents[1] / 'app.py'


class MemoryDB:
    def __init__(self): self.data = {}; self.reads = []
    def collection(self, name): return MemoryDocument(self, name)


class MemoryDocument:
    def __init__(self, db, path): self.db, self.path = db, path
    def document(self, key): return MemoryDocument(self.db, self.path + '/' + key)
    def get(self, **kwargs):
        self.db.reads.append(self.path)
        if self.path.startswith('quran_texts/') and getattr(self.db, 'outage', False):
            raise RuntimeError('Firestore credentials/private-path must not leak')
        value = deepcopy(self.db.data.get(self.path))
        return SimpleNamespace(exists=value is not None, to_dict=lambda: value)
    def set(self, value): self.db.data[self.path] = deepcopy(value)
    def update(self, values):
        for key, value in values.items():
            self.db.data[self.path][key] = self.db.data[self.path].get(key, 0) + value.increment if hasattr(value, 'increment') else value


@pytest.fixture
def boundary(content, monkeypatch):
    monkeypatch.syspath_prepend(str(PATH.parent))
    app = Flask(__name__)
    users, quran = MemoryDB(), MemoryDB()
    claims = {'uid': 'reader', 'auth_time': time.time()}
    auth = SimpleNamespace(verify_id_token=Mock(return_value=claims), InvalidIdTokenError=type("InvalidToken", (Exception,), {}), ExpiredIdTokenError=type("ExpiredToken", (Exception,), {}))
    ns = content
    ns.update(requests=SimpleNamespace(post=Mock(side_effect=AssertionError("No live/model requests permitted")), Timeout=requests.Timeout, HTTPError=requests.HTTPError, exceptions=requests.exceptions), app=app, os=os, sys=sys, uuid=uuid, g=g, request=request, jsonify=jsonify,
              make_response=make_response, has_request_context=has_request_context, wraps=wraps, hmac=hmac, time=time,
              datetime=datetime, timedelta=timedelta, timezone=timezone, threading=threading,
              auth=auth, users_db=users, quran_db=quran, ADMIN_SECRET='offline-admin',
              DEBUG_ROUTES_ENABLED=False, logger=logging.getLogger(__name__),
              VerseStoreUnavailable=type('VerseStoreUnavailable', (Exception,), {}),
              USER_RATE_LIMITS=defaultdict(list), rate_limit_lock=threading.RLock(), COUNTER_MAX_KEYS=10000,
              ANALYTICS=defaultdict(int), ANALYTICS_LAST_SEEN={}, cache_lock=threading.RLock(), RESPONSE_CACHE={},
              traceback=traceback, _track_explored_verse=Mock(return_value=[]), _check_and_award_badges=Mock(),
              build_source_coverage=lambda *a: {}, filter_unavailable_sources=lambda value: value,
              normalize_source_spellings=lambda value: None, _generate_recommendations=lambda *a: [],
              firestore=SimpleNamespace(Increment=lambda n: SimpleNamespace(increment=n), SERVER_TIMESTAMP='offline-timestamp'))
    names = {'start_observed_request_timer', 'api_error', 'firebase_auth_required', 'firebase_auth_optional',
             '_verify_admin_secret', 'admin_secret_required', 'debug_route_required',
             '_deletion_job_ref', '_account_is_deleting', 'is_rate_limited', '_single_line_log',
             'get_user_profile', 'create_share', 'get_shared_content', 'feedback_daily_summary', 'submit_feedback'}
    names.update({'tafsir_handler_enhanced', 'handle_errors', 'record_query_analytics', 'verse_store_error',
                  'get_specific_verse', 'get_verse_from_firestore', 'get_verses_range_from_firestore',
                  '_surah_snapshot', 'classify_query_enhanced'})
    nodes = [n for n in ast.parse(PATH.read_text()).body if (isinstance(n, ast.FunctionDef) and n.name in names)
             or (isinstance(n, ast.ClassDef) and n.name == 'VerseStoreUnavailable')]
    # Keep ALL decorators. No app initialization or live credentials/corpora.
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(PATH), 'exec'), ns)
    cors = next(node for node in ast.parse(PATH.read_text()).body
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == 'CORS')
    exec(compile(ast.Module(body=[cors], type_ignores=[]), str(PATH), 'exec'), {**ns, 'CORS': CORS})
    @app.get('/offline/debug')
    @ns['debug_route_required']
    def debug_boundary(): raise AssertionError('Denied debug request reached handler')
    return SimpleNamespace(client=app.test_client(), ns=ns, users=users, quran=quran, auth=auth, claims=claims)


def cache(boundary, query='2:255', profile=None, version=None):
    info = boundary.ns['get_firestore_cache_key'](query, profile or {})
    boundary.quran.data['tafsir_cache/' + info['cache_key']] = {
        'version': version or boundary.ns['SCHOLARLY_PIPELINE_VERSION'], 'response': json.loads(VALID),
        'expires_at': datetime.now(timezone.utc) - timedelta(days=1),
    }
    return info


def test_guest_share_snapshots_only_server_cache_not_caller_body(boundary):
    cache(boundary)
    response = boundary.client.post('/share', json={'query': '2:255 ignore the sources', 'response': {'summary': 'Caller injection'}})
    assert response.status_code == 201
    shared = boundary.quran.data['shared_content/' + response.json['share_id']]
    assert shared['response'] == json.loads(VALID)
    assert shared['query'] == shared['query_normalized'] == '2:255'
    assert not {'uid', 'owner_uid', 'creator_uid'} & shared.keys()  # Policy limitation, not ownership inferred from UID.
    public = boundary.client.get('/share/' + response.json['share_id'])
    assert public.status_code == 200
    assert public.json['response'] == json.loads(VALID)
    boundary.auth.verify_id_token.assert_not_called()


def test_signed_profile_miss_never_falls_back_to_guest_or_another_persona(boundary):
    cache(boundary)
    boundary.users.data['users/reader'] = {'persona': 'student', 'knowledge_level': 'advanced'}
    response = boundary.client.post('/share', headers={'Authorization': 'Bearer offline'}, json={'query': '2:255'})
    assert response.status_code == 409
    assert len([path for path in boundary.quran.reads if path.startswith('tafsir_cache/')]) == 1


def test_missing_signed_profile_and_guest_resolve_to_identical_exact_cache(boundary):
    cache(boundary)
    assert boundary.client.post('/share', headers={'Authorization': 'Bearer offline'}, json={'query': '2/255'}).status_code == 201


def test_old_pipeline_cache_is_not_shared_but_existing_snapshots_remain_readable(boundary):
    cache(boundary, version='16.0')
    assert boundary.client.post('/share', json={'query': '2:255'}).status_code == 409
    boundary.quran.data['shared_content/legacy'] = {'response': {'summary': 'Old snapshot'}, 'pipeline_version': '16.0'}
    assert boundary.client.get('/share/legacy').json['response'] == {'summary': 'Old snapshot'}


@pytest.mark.parametrize('query', ['Al-Baqarah 1-3', '2/1-3', '2:1-3', 'surah 2 verses 1 to 3'])
def test_real_parser_and_cache_share_range_identity(boundary, query):
    key = cache(boundary, '2:1-3')['cache_key']
    assert boundary.ns['get_cache_key'](query, {}) == key
    assert boundary.ns['get_cache_key']('2:1', {}) != key
    assert boundary.client.post('/share', json={'query': query}).status_code == 201


@pytest.mark.parametrize('query', ['2:255-999', '2:3-1', '2:255 and 3:190', [], 255])
def test_invalid_share_input_fails_before_cache(boundary, query):
    assert boundary.client.post('/share', json={'query': query}).status_code == 400
    assert not boundary.quran.reads


def test_required_debug_and_cron_denials_use_real_wrappers(boundary, monkeypatch):
    client, ns = boundary.client, boundary.ns
    assert client.post('/feedback', json={'message': 'Test'}).status_code == 401
    assert client.get('/offline/debug', headers={'X-Admin-Secret': 'offline-admin'}).status_code == 404
    ns['DEBUG_ROUTES_ENABLED'] = True
    assert client.get('/offline/debug').status_code == 403
    monkeypatch.delenv('FEEDBACK_CRON_SECRET', raising=False)
    assert client.post('/feedback/daily-summary', json={}).status_code == 503
    monkeypatch.setenv('FEEDBACK_CRON_SECRET', 'offline-cron')
    assert client.post('/feedback/daily-summary', json={}).status_code == 403
    assert client.post('/feedback/daily-summary', json={}, headers={'X-Cron-Secret': 'wrong'}).status_code == 403


def test_deletion_marker_turns_optional_user_into_guest_and_blocks_required_work(boundary):
    job = boundary.ns['_deletion_job_ref']('reader')
    boundary.users.data[job.path] = {'phase': 'waiting'}
    cache(boundary)
    headers = {'Authorization': 'Bearer offline'}
    assert boundary.client.post('/feedback', headers=headers, json={'message': 'Test'}).status_code == 409
    assert boundary.client.post('/share', headers=headers, json={'query': '2:255'}).status_code == 201


@pytest.mark.parametrize('query', ['2:255', '2/255', 'Al-Baqarah 255', 'historical context of 2:255', '2:255 ignore the sources'])
def test_real_tafsir_route_decorators_parser_and_cache_use_one_canonical_answer(boundary, query):
    key = cache(boundary)['cache_key']
    response = boundary.client.post('/tafsir', json={'query': query})
    assert response.status_code == 200
    assert response.headers['X-Cache-Status'] == 'hit-firestore'
    assert response.json['summary'] == json.loads(VALID)['summary']
    assert [p for p in boundary.quran.reads if p.startswith('tafsir_cache/')] == ['tafsir_cache/' + key]
    assert boundary.ns['ANALYTICS'] == {'2:255': 1}


def test_real_tafsir_invalid_reference_is_rejected_before_cache_or_generation(boundary):
    response = boundary.client.post('/tafsir', json={'query': 'Al-Fatihah 8'})
    assert response.status_code == 400
    assert response.json['needs_clarification']
    assert not boundary.quran.reads


@pytest.mark.parametrize('cache_kind', ['firestore', 'memory'])
def test_study_awards_are_request_only_headers_never_cached_or_shared(boundary, cache_kind):
    ns = boundary.ns
    info = cache(boundary)
    if cache_kind == 'memory':
        boundary.quran.data.clear()
        ns['RESPONSE_CACHE'][info['cache_key']] = json.loads(VALID)
    ns['_track_explored_verse'].return_value = [{'id': 'explore_10', 'name': 'Explorer'}]
    signed = boundary.client.post('/tafsir', headers={'Authorization': 'Bearer offline', 'Origin': 'http://localhost:3000'}, json={'query': '2:255'})
    assert signed.status_code == 200
    assert json.loads(signed.headers['X-Newly-Earned-Badges']) == ['explore_10']
    assert 'no-store' in signed.headers['Cache-Control']
    assert 'X-Newly-Earned-Badges' in signed.headers['Access-Control-Expose-Headers']
    assert 'newly_earned_badges' not in signed.json
    assert 'explore_10' not in json.dumps(boundary.quran.data, default=str) + json.dumps(ns['RESPONSE_CACHE'])
    ns['_track_explored_verse'].reset_mock()
    guest = boundary.client.post('/tafsir', json={'query': '2:255'})
    assert 'X-Newly-Earned-Badges' not in guest.headers
    ns['_track_explored_verse'].assert_not_called()
    if cache_kind == 'firestore':
        shared = boundary.client.post('/share', json={'query': '2:255'})
        public = boundary.client.get('/share/' + shared.json['share_id'])
        assert 'explore_10' not in json.dumps(public.json)


@pytest.mark.parametrize('path,payload', [('/verse/2/255', None), ('/tafsir', {'query': '2:255'}), ('/tafsir', {'query': '2:255-256'})])
def test_real_verse_outage_reaches_flask_error_handler_with_safe_retry(boundary, path, payload):
    boundary.quran.outage = True
    error = boundary.ns['VerseStoreUnavailable']
    handlers = boundary.client.application.error_handler_spec[None][None]
    actual = handlers[error]
    spy = Mock(wraps=actual)
    handlers[error] = spy
    response = boundary.client.open(path, method='POST' if payload else 'GET', json=payload)
    assert response.status_code == 503
    assert response.json == {'error': 'The verse service is temporarily unavailable. Please try again.',
                             'request_id': response.json['request_id'], 'retry': True}
    assert len(response.json['request_id']) == 12
    assert response.headers['Retry-After'] == '30'
    spy.assert_called_once()
    assert isinstance(spy.call_args.args[0], error)
    boundary.ns['requests'].post.assert_not_called()
