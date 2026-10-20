import ast
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import logging
from pathlib import Path
import threading
import traceback
from types import SimpleNamespace

from flask import Flask, g, has_request_context, jsonify, request
import pytest

PATH = Path(__file__).resolve().parents[1] / 'app.py'


class Store:
    def __init__(self):
        self.docs = {'users/reader': {'annotation_count': 1000}}
        self.lock = threading.RLock(); self.commits = 0; self.aggregations = 0
    def collection(self, name): return Collection(self, name)
    def transaction(self): return self
    def set(self, reference, data, merge=False):
        self.docs[reference.path] = {**self.docs.get(reference.path, {}), **deepcopy(data)}
    def delete(self, reference): self.docs.pop(reference.path, None)
    def transactional(self, function):
        def run(tx):
            with self.lock:
                result = function(tx)
                self.commits += 1
                return result
        return run


class Document:
    def __init__(self, store, path): self.store, self.path = store, path
    @property
    def id(self): return self.path.rsplit('/', 1)[-1]
    def collection(self, name): return Collection(self.store, self.path + '/' + name)
    def get(self, transaction=None):
        value = deepcopy(self.store.docs.get(self.path))
        return SimpleNamespace(exists=value is not None, to_dict=lambda: value)


class Collection:
    def __init__(self, store, path): self.store, self.path = store, path
    def document(self, key=None): return Document(self.store, self.path + '/' + (key or 'new-annotation'))
    def count(self): return self
    def get(self, transaction=None):
        self.store.aggregations += 1
        return [[SimpleNamespace(value=sum(p.startswith(self.path + '/') for p in self.store.docs))]]
    def stream(self): raise AssertionError('Progress/badge checks must never stream annotations')


@pytest.fixture
def progress():
    store = Store()
    names = {'_deletion_job_ref', '_update_user_transaction', '_streak_updates', '_annotation_count',
             '_track_explored_verse', '_check_and_award_badges', 'update_plan_progress', '_surah_snapshot', '_page_documents'}
    names.update({'create_annotation', 'delete_annotation'})
    tree = ast.parse(PATH.read_text())
    nodes = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
             or (isinstance(n, ast.ClassDef) and n.name == 'PageRequestError')]
    for node in nodes: node.decorator_list = []
    ns = dict(users_db=store, gcp_firestore=SimpleNamespace(transactional=store.transactional),
              datetime=datetime, timedelta=timedelta, timezone=timezone, hashlib=hashlib,
              logger=logging.getLogger(__name__), request=request, jsonify=jsonify, g=g,
              has_request_context=has_request_context,
              firestore=SimpleNamespace(SERVER_TIMESTAMP='timestamp'), traceback=traceback,
              _encrypt_text=lambda text, uid: text,
              READING_PLANS=[{'id': 'fixture', 'duration_days': 3, 'days': [{'verse': (2, v)} for v in (1, 2, 3)]}],
              THEMED_COLLECTIONS=[{'id': 'fixture', 'verses': [(2, 1, 'One'), (2, 2, 'Two')]}],
              _VERSE_TO_COLLECTIONS={'2:1': ['fixture'], '2:2': ['fixture']},
              api_error=lambda: (jsonify({'error': 'Failed'}), 500))
    definition = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'BADGE_DEFINITIONS' for t in n.targets))
    exec(compile(ast.Module(body=[definition, *nodes], type_ignores=[]), str(PATH), 'exec'), ns)
    return store, ns


def test_concurrent_studies_keep_every_verse_and_consistent_counts(progress):
    store, ns = progress
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda v: ns['_track_explored_verse']('reader', 2, v), range(1, 31)))
    data = store.docs['users/reader']
    assert data['explored_verses']['2'] == list(range(1, 31))
    assert data['stats_cache']['total_explored_verses'] == 30
    assert data['collection_progress']['fixture']['explored'] == ['2:1', '2:2']
    assert store.commits == 30


def test_highest_reflection_badge_uses_maintained_count_without_stream(progress):
    store, ns = progress
    awarded = ns['_check_and_award_badges']('reader')
    assert 'reflect_1000' in {item['id'] for item in awarded}
    assert store.aggregations == 0
    assert not {'comeback_7', 'daily_verse_7', 'first_week'} & ns['BADGE_DEFINITIONS'].keys()


def test_legacy_count_seeds_once_using_index_aggregation(progress):
    store, ns = progress
    store.docs['users/reader'] = {}
    store.docs['users/reader/annotations/one'] = {'content': 'private'}
    ns['_check_and_award_badges']('reader'); ns['_check_and_award_badges']('reader')
    assert store.aggregations == 1
    assert store.docs['users/reader']['annotation_count'] == 1


@pytest.mark.parametrize('bad', [True, False, 1.5, '1', 0, 4, None])
def test_invalid_plan_days_fail_before_transaction(progress, bad):
    store, ns = progress
    app = Flask(__name__)
    with app.test_request_context(json={'action': 'complete_day', 'day': bad}):
        request.user = {'uid': 'reader'}
        assert ns['update_plan_progress']('fixture')[1] == 400
    assert store.commits == 0


def test_out_of_order_plan_completion_and_retries_never_rewind(progress):
    store, ns = progress
    app = Flask(__name__)
    def action(payload):
        with app.test_request_context(json=payload):
            request.user = {'uid': 'reader'}
            response, status = ns['update_plan_progress']('fixture')
            assert status == 200
            return response.json
    action({'action': 'start'})
    assert action({'action': 'complete_day', 'day': 2})['current_day'] == 1
    assert action({'action': 'complete_day', 'day': 1})['current_day'] == 3
    assert action({'action': 'complete_day', 'day': 1})['current_day'] == 3
    action({'action': 'complete_day', 'day': 3})
    completed = deepcopy(store.docs['users/reader']['active_plans']['fixture'])
    action({'action': 'complete_day', 'day': 1})
    assert store.docs['users/reader']['active_plans']['fixture'] == completed


def test_study_transaction_cannot_recreate_deleting_account(progress):
    store, ns = progress
    job = ns['_deletion_job_ref']('reader')
    store.docs[job.path] = {'phase': 'waiting'}
    ns['_track_explored_verse']('reader', 2, 1)
    assert 'explored_verses' not in store.docs['users/reader']


def test_surah_snapshot_is_read_once_per_request(progress):
    from unittest.mock import Mock
    ns = progress[1]; db = Mock(); ns['quran_db'] = db
    app = Flask(__name__)
    with app.test_request_context():
        for _ in range(10): ns['_surah_snapshot'](2)
        ns['_surah_snapshot'](3)
    assert db.collection.return_value.document.return_value.get.call_count == 2


def test_annotation_create_delete_and_delete_retry_keep_exact_count(progress):
    store, ns = progress
    store.docs['users/reader']['annotation_count'] = 0
    app = Flask(__name__)
    with app.test_request_context(json={'content': 'Reflection', 'reflection_type': 'general'}):
        request.user = {'uid': 'reader'}
        assert ns['create_annotation']()[1] == 201
        assert store.docs['users/reader']['annotation_count'] == 1
        assert ns['delete_annotation']('new-annotation')[1] == 200
        assert ns['delete_annotation']('new-annotation')[1] == 200
    assert store.docs['users/reader']['annotation_count'] == 0


def test_completed_plan_restarts_fresh_but_in_progress_start_is_idempotent(progress):
    store, ns = progress
    app = Flask(__name__)
    def action(payload):
        with app.test_request_context(json=payload):
            request.user = {'uid': 'reader'}
            response, status = ns['update_plan_progress']('fixture')
            assert status == 200
            return response.json
    action({'action': 'start'})
    action({'action': 'complete_day', 'day': 1})
    action({'action': 'start'})  # repeat Start mid-plan keeps progress
    assert store.docs['users/reader']['active_plans']['fixture']['completed_days'] == [1]
    for day in (2, 3):
        action({'action': 'complete_day', 'day': day})
    assert store.docs['users/reader']['active_plans']['fixture']['completed_at']
    action({'action': 'start'})  # the plans page offers Start again once complete
    restarted = store.docs['users/reader']['active_plans']['fixture']
    assert restarted['completed_days'] == [] and restarted['current_day'] == 1
    assert restarted['completed_at'] is None
