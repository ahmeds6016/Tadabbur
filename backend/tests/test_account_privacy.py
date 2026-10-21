import ast
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest.mock import Mock

from cryptography.fernet import Fernet
from flask import Flask, jsonify, make_response, request
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_versioned_crypto_and_idempotent_migration_functions():
    names = {'_get_user_fernet', '_encrypt_text', '_decrypt_text'}
    nodes = [n for n in ast.parse((ROOT / 'app.py').read_text()).body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = dict(REFLECTION_ENCRYPTION_SECRET='offline-key', CIPHERTEXT_PREFIX='fernet:v1:',
              Fernet=Fernet, Optional=Optional, hashlib=hashlib, hmac=hmac, base64=base64)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'crypto', 'exec'), ns)
    value = ns['_encrypt_text']('Private reflection', 'reader')
    assert value.startswith('fernet:v1:')
    assert ns['_decrypt_text'](value, 'reader') == 'Private reflection'
    assert ns['_decrypt_text']('Legacy plain text', 'reader') == 'Legacy plain text'
    cipher = ns['_get_user_fernet']('reader')
    old_ciphertext = cipher.encrypt(b'Old encrypted text').decode()
    assert ns['_decrypt_text'](old_ciphertext, 'reader') == 'Old encrypted text'
    spec = importlib.util.spec_from_file_location('migration_review_only', ROOT / 'scripts/encrypt_existing_reflections.py')
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)  # Pure helpers only; main() is never called.
    updates = migration.migrate_fields({'content': old_ciphertext, 'highlighted_text': 'Highlight'}, 'annotations', cipher)
    assert ns['_decrypt_text'](updates['content'], 'reader') == 'Old encrypted text'
    assert migration.migrate_fields(updates, 'annotations', cipher) == {}
    with pytest.raises(ValueError):
        migration.migrate_fields({'content': old_ciphertext}, 'annotations', Fernet(Fernet.generate_key()))
    ns['REFLECTION_ENCRYPTION_SECRET'] = ''
    assert ns['_decrypt_text']('Legacy plain text', 'reader') == 'Legacy plain text'
    with pytest.raises(RuntimeError): ns['_decrypt_text'](value, 'reader')


class Document:
    def __init__(self, data=None):
        self.data, self.children = data, {}
        self.reference = self
    def get(self): return self
    @property
    def exists(self): return self.data is not None
    def to_dict(self): return deepcopy(self.data)
    def create(self, data): self.data = data
    def set(self, data, merge=False): self.data = {**(self.data or {}), **data} if merge else data
    def delete(self): self.data = None
    def collection(self, name): return self.children.setdefault(name, Collection())
    def collections(self): return list(self.children.values())


class Collection:
    def __init__(self): self.docs = {}; self.maximum = 1000
    def document(self, key): return self.docs.setdefault(key, Document())
    def limit(self, size): self.maximum = size; return self
    def stream(self): return iter([v for v in self.docs.values() if v.exists][:self.maximum])
    def list_documents(self, **kwargs): return iter([v for v in self.docs.values() if v.exists or any(list(c.stream()) for c in v.collections())])
    def where(self, **kwargs): return self


@pytest.fixture
def erasure():
    collections = {}
    db = SimpleNamespace(collection=lambda key: collections.setdefault(key, Collection()))
    now = [1000]
    firebase = SimpleNamespace(revoke_refresh_tokens=Mock(), delete_user=Mock(), UserNotFoundError=type('MissingUser', (Exception,), {}))
    ns = dict(users_db=db, hashlib=hashlib, request=request, jsonify=jsonify, make_response=make_response,
              time=SimpleNamespace(time=lambda: now[0]), auth=firebase,
              datetime=datetime, timedelta=timedelta, timezone=timezone,
              firestore=SimpleNamespace(SERVER_TIMESTAMP='timestamp'), FieldFilter=lambda *a: a,
              api_error=lambda: (jsonify({'error': 'Please retry.'}), 500))
    names = {'_deletion_job_ref', '_account_is_deleting', '_erase_descendants_page', 'delete_account'}
    nodes = [n for n in ast.parse((ROOT / 'app.py').read_text()).body if isinstance(n, ast.FunctionDef) and n.name in names]
    for node in nodes: node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'account', 'exec'), ns)
    app = Flask(__name__)
    claims = {'uid': 'reader', 'auth_time': 1000}
    @app.before_request
    def account(): request.user = claims
    app.add_url_rule('/', view_func=ns['delete_account'], methods=['POST'])
    return app.test_client(), ns, db, firebase, now, claims


def test_erasure_is_bounded_resumable_and_auth_is_last(erasure):
    client, ns, db, firebase, now, _ = erasure
    root = db.collection('users').document('reader'); root.set({'persona': 'student'})
    for index in range(101): root.collection('annotations').document(str(index)).set({'content': 'private'})
    for collection in ('iman_correlation_narratives', 'iman_struggle_goals', 'query_history', 'saved_searches', 'iman_config', 'iman_daily_logs', 'iman_baselines', 'iman_trajectory', 'iman_struggles', 'iman_weekly_digests', 'iman_daily_insights'):
        root.collection(collection).document('record').set({'private': True})
    root.collection('legacy').document('missing-parent').collection('nested').document('child').set({'private': True})
    db.collection('feedback').document('feedback').set({'uid': 'reader'})
    assert client.post('/', json={'confirmation': 'DELETE'}).status_code == 202
    assert ns['_account_is_deleting']('reader')
    firebase.delete_user.assert_not_called()
    now[0] += 306
    assert client.post('/', json={'confirmation': 'DELETE'}).status_code == 202
    firebase.delete_user.assert_not_called()
    def auth_last(uid):
        assert not root.exists
        assert not list(db.collection('feedback').stream())
        assert all(not list(col.stream()) for col in root.collections())
    firebase.delete_user.side_effect = auth_last
    marker = ns['_deletion_job_ref']('reader')
    assert 'expires_at' not in marker.to_dict()  # An unfinished job must keep gating the account.
    assert client.post('/', json={'confirmation': 'DELETE'}).json['complete']
    assert client.post('/', json={'confirmation': 'DELETE'}).json['complete']
    firebase.delete_user.assert_called_once()
    # The privacy notice promises the marker is removed 30 days after completion.
    remaining = marker.to_dict()['expires_at'] - datetime.now(timezone.utc)
    assert timedelta(days=29, hours=23) < remaining <= timedelta(days=30)


def test_deletion_requires_recent_auth_and_confirmation(erasure):
    client, _, _, firebase, now, claims = erasure
    assert client.post('/', json={}).status_code == 400
    claims['auth_time'] = now[0] - 301
    assert client.post('/', json={'confirmation': 'DELETE'}).status_code == 401
    firebase.delete_user.assert_not_called()


def test_erasure_resumes_after_auth_service_failure(erasure):
    client, _, db, firebase, now, _ = erasure
    db.collection('users').document('reader').set({'private': True})
    assert client.post('/', json={'confirmation': 'DELETE'}).status_code == 202
    now[0] += 306
    firebase.delete_user.side_effect = [RuntimeError('offline failure'), None]
    assert client.post('/', json={'confirmation': 'DELETE'}).status_code == 500
    assert client.post('/', json={'confirmation': 'DELETE'}).json['complete']
