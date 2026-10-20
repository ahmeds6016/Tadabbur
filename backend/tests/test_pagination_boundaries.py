import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from flask import Flask, jsonify, request
import pytest

PATH = Path(__file__).resolve().parents[1] / 'app.py'


class Database:
    def __init__(self): self.docs = {}; self.reads = []; self.queries = []
    def collection(self, path): return Query(self, path)


class Document:
    def __init__(self, db, path): self.db, self.path, self.id = db, path, path.rsplit('/', 1)[-1]
    def collection(self, name): return Query(self.db, self.path + '/' + name)
    def get(self, field_paths=None):
        self.db.reads.append((self.path, field_paths))
        return self.snapshot(field_paths)
    def snapshot(self, fields=None):
        data = deepcopy(self.db.docs.get(self.path))
        if data is not None and fields is not None: data = {key: data[key] for key in fields if key in data}
        return SimpleNamespace(id=self.id, exists=self.path in self.db.docs, reference=self, to_dict=lambda: data)


class Query:
    def __init__(self, db, path, fields=None, order='__name__', maximum=None, cursor=None):
        self.db, self.path, self.fields, self.order, self.maximum, self.cursor = db, path, fields, order, maximum, cursor
    def document(self, key): return Document(self.db, self.path + '/' + key)
    def clone(self, **kwargs):
        values = dict(fields=self.fields, order=self.order, maximum=self.maximum, cursor=self.cursor); values.update(kwargs)
        return Query(self.db, self.path, **values)
    def select(self, fields): return self.clone(fields=fields)
    def order_by(self, field, **kwargs): return self.clone(order=field)
    def limit(self, value): return self.clone(maximum=value)
    def start_after(self, snapshot): return self.clone(cursor=snapshot.id)
    def stream(self):
        self.db.queries.append((self.maximum, self.fields))
        assert self.maximum is not None and self.maximum <= 101
        paths = sorted((p for p in self.db.docs if p.startswith(self.path + '/')), reverse=True)
        if self.cursor: paths = [p for p in paths if p.rsplit('/', 1)[-1] < self.cursor]
        return iter([Document(self.db, path).snapshot(self.fields) for path in paths[:self.maximum]])


@pytest.fixture
def lists():
    db = Database()
    names = {'_page_documents', 'get_saved_searches', 'get_saved_answer', 'get_query_history'}
    nodes = [n for n in ast.parse(PATH.read_text()).body if isinstance(n, ast.FunctionDef) and n.name in names]
    for node in nodes: node.decorator_list = []
    ns = dict(users_db=db, jsonify=jsonify, request=request, api_error=lambda: (jsonify({'error': 'Failed'}), 500))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(PATH), 'exec'), ns)
    app = Flask(__name__)
    @app.before_request
    def account(): request.user = {'uid': request.headers.get('X-Offline-User', 'A')}
    app.add_url_rule('/saved', view_func=ns['get_saved_searches'])
    app.add_url_rule('/saved/<search_id>', view_func=ns['get_saved_answer'])
    app.add_url_rule('/history', view_func=ns['get_query_history'])
    for index in range(5):
        db.docs[f'users/A/saved_searches/{index}'] = {'query': '2:255', 'savedAt': index, 'fullResponse': {'summary': 'Private stored snapshot'}}
        db.docs[f'users/A/query_history/{index}'] = {'query': '2:255', 'timestamp': index}
    return app.test_client(), db, ns


@pytest.mark.parametrize('route,key', [('/saved', 'saved'), ('/history', 'history')])
def test_pages_are_bounded_disjoint_and_omit_full_answers(lists, route, key):
    client, db, _ = lists
    first = client.get(route + '?limit=2').json
    second = client.get(route + '?limit=2&cursor=' + first['next_cursor']).json
    assert len(first[key]) == len(second[key]) == 2
    assert not {d['id'] for d in first[key]} & {d['id'] for d in second[key]}
    assert all('fullResponse' not in d for d in first[key])
    assert all(maximum == 3 for maximum, fields in db.queries)
    assert all(fields is not None and 'fullResponse' not in fields for maximum, fields in db.queries)
    assert db.reads[0][1] == ['savedAt' if key == 'saved' else 'timestamp']


def test_full_saved_snapshot_is_fetched_only_on_demand_and_owner_scoped(lists):
    client, db, _ = lists
    assert client.get('/saved/1').json['response']['summary'] == 'Private stored snapshot'
    assert client.get('/saved/1', headers={'X-Offline-User': 'B'}).status_code == 404
    assert len(db.reads) == 2


@pytest.mark.parametrize('query', ['limit=0', 'limit=-1', 'limit=101', 'limit=no', 'cursor=missing', 'cursor=x/y'])
def test_invalid_page_inputs_return_400(lists, query):
    assert lists[0].get('/saved?' + query).status_code == 400
