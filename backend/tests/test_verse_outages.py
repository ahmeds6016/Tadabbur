import ast
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from flask import Flask, jsonify


@pytest.fixture
def verses():
    path = Path(__file__).resolve().parents[1] / 'app.py'
    tree = ast.parse(path.read_text())
    names = {'get_verse_from_firestore', 'get_verses_range_from_firestore', 'get_daily_verse'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    for node in nodes: node.decorator_list = []
    error = type('VerseStoreUnavailable', (RuntimeError,), {})
    db = Mock()
    ns = dict(quran_db=db, QURAN_METADATA={2: {'name': 'Al-Baqarah'}}, VerseStoreUnavailable=error,
              datetime=datetime, timezone=timezone, hashlib=hashlib, DAILY_VERSE_POOL=[(2, 255, 'Theme')],
              jsonify=jsonify, api_error=lambda: (jsonify({'error': 'Please try again.', 'retry': True}), 503))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), ns)
    return ns, db, error


def test_missing_verse_differs_from_dependency_failure(verses):
    ns, db, error = verses
    doc = db.collection.return_value.document.return_value.get
    doc.return_value.exists = False
    assert ns['get_verse_from_firestore'](2, 255) is None
    doc.side_effect = RuntimeError('database unavailable')
    with pytest.raises(error): ns['get_verse_from_firestore'](2, 255)
    with pytest.raises(error): ns['get_verses_range_from_firestore'](2, 255, 256)


@pytest.mark.parametrize('value', [None, {'arabic': '', 'english': ''}])
def test_daily_verse_never_returns_empty_success(verses, value):
    ns, _, _ = verses
    ns['get_verse_from_firestore'] = lambda *a: value
    app = Flask(__name__)
    app.add_url_rule('/', view_func=ns['get_daily_verse'])
    assert app.test_client().get('/').status_code == 503
