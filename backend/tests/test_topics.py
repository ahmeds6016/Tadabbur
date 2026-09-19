"""Grounded index, closed vocabulary, and offline /topics/resolve coverage."""

import ast
import json
from pathlib import Path
import re

import pytest
import requests

from backend.tests.topic_harness import make_topic_app, model_response
from services.topic_service import (
    build_topic_index, topic_candidates, topic_mapping_body, validate_topic_mapping,
)

INDEX = build_topic_index()
VALID = {"topics": [{"name": "Patience", "confidence": 0.9}]}


def test_index_matches_eight_existing_curated_themes_and_canonical_bounds():
    root = Path(__file__).resolve().parents[2]
    source = (root / 'frontend/app/components/SurahVersePicker.jsx').read_text()
    themes = source.split('export const THEME_QUICK_SELECTS = [', 1)[1].split('\n];', 1)[0]
    extracted = {name: re.findall(r"\['(\d+:\d+)'", body)
                 for name, body in re.findall(r"label: '([^']+)',\s+verses: themeVerses\(\[(.*?)\]\)", themes, re.S)}
    assert len(INDEX) == len(extracted) == 8
    assert {name: topic['verse_refs'] for name, topic in INDEX.items()} == extracted
    tree = ast.parse((root / 'backend/app.py').read_text())
    metadata = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == 'QURAN_METADATA' for t in node.targets))
    for topic in INDEX.values():
        for ref in topic['verse_refs']:
            surah, verse = map(int, ref.split(':'))
            assert 1 <= verse <= metadata[surah]['verses']
    assert INDEX == build_topic_index()


def test_keyword_candidates_reuse_scholarly_synonyms():
    assert 'sabr' in INDEX['Patience']['keywords']
    assert 'tawakkul' in INDEX['Trust in Allah']['keywords']
    assert topic_candidates('tawakkul and reliance', INDEX)[0] == 'Trust in Allah'
    assert set(topic_candidates('unmatched', INDEX)) == set(INDEX)


def test_seed_order_and_duplicate_refs_are_deterministic():
    index = build_topic_index([{'name': 'Patience', 'verse_refs': ['3:200', '2:153', '3:200']}])
    assert index['Patience']['verse_refs'] == ['3:200', '2:153']


def test_closed_schema_and_thinking_safe_budget():
    body = topic_mapping_body('patience during hardship', INDEX)
    config = body['generation_config']
    assert config['maxOutputTokens'] == 4096
    schema = config['response_schema']['properties']['topics']
    assert schema['maxItems'] == 3
    assert schema['items']['properties']['name']['enum'] == list(INDEX)
    assert 'verse_refs' not in schema['items']['properties']


@pytest.mark.parametrize('value', [
    None, [], {}, {'topics': None}, {'topics': []}, {'topics': ['Patience']},
    {'topics': [{'name': 'Invented', 'confidence': 1}]},
    {'topics': [{'name': None, 'confidence': 1}]},
    {'topics': [{'name': 'Patience'}]},
    {'topics': [{'name': 'Patience', 'confidence': True}]},
    {'topics': [{'name': 'Patience', 'confidence': 'high'}]},
    *[{'topics': [{'name': 'Patience', 'confidence': score}]} for score in [-1, 2, float('nan'), float('inf')]],
    {'topics': [{'name': 'Patience', 'confidence': 1, 'verse_refs': ['99:99']}]},
    {'topics': VALID['topics'] * 2},
    {'topics': [{'name': name, 'confidence': 1} for name in list(INDEX)[:4]]},
    {'topics': VALID['topics'], 'verse_refs': ['99:99']},
])
def test_mapping_rejects_out_of_contract_output(value):
    with pytest.raises(ValueError):
        validate_topic_mapping(value, INDEX)


def test_valid_mapping_attaches_only_index_refs_and_does_not_mutate_index():
    result = validate_topic_mapping(VALID, INDEX)
    assert result == [{'name': 'Patience', 'confidence': 0.9, 'verse_refs': ['2:153', '3:200', '39:10']}]
    result[0]['verse_refs'].append('99:99')
    assert '99:99' not in INDEX['Patience']['verse_refs']


def test_guest_endpoint_uses_lite_and_normalized_memory_cache():
    env = make_topic_app()
    env.post.return_value = model_response(VALID)
    first = env.client.post('/topics/resolve', json={'text': 'Patience during hardship'})
    second = env.client.post('/topics/resolve', json={'text': ' patience  DURING hardship '})
    assert first.status_code == second.status_code == 200
    assert first.json == second.json == {'topics': validate_topic_mapping(VALID, INDEX)}
    env.post.assert_called_once()
    call = env.post.call_args
    assert 'gemini-3.5-flash-lite:generateContent' in call.args[0]
    assert call.kwargs['timeout'] == 20
    assert call.kwargs['json']['generation_config']['maxOutputTokens'] == 4096


@pytest.mark.parametrize('failure', ['network', 'unknown', 'empty', 'malformed'])
def test_mapping_failure_returns_eight_curated_suggestions(failure):
    env = make_topic_app()
    if failure == 'network':
        env.post.side_effect = requests.Timeout()
    elif failure == 'malformed':
        response = model_response(VALID)
        response._content = b'not json'
        env.post.return_value = response
    else:
        env.post.return_value = model_response({'topics': []} if failure == 'empty' else
                                              {'topics': [{'name': 'Unknown', 'confidence': 1}]})
    result = env.client.post('/topics/resolve', json={'text': 'a life question'})
    assert result.status_code == 200
    assert [topic['name'] for topic in result.json['topics']] == list(INDEX)
    assert all(topic['confidence'] == 0 for topic in result.json['topics'])
    assert env.post.call_count == 1


@pytest.mark.parametrize('value', [None, [], {}, {'text': None}, {'text': 7}, {'text': ''}, {'text': ' '}, {'text': 'x' * 501}])
def test_bad_requests_still_include_browsable_suggestions(value):
    env = make_topic_app()
    response = env.client.post('/topics/resolve', data=json.dumps(value), content_type='application/json')
    assert response.status_code == 400
    assert len(response.json['topics']) == 8
    env.post.assert_not_called()


def test_curated_theme_needs_no_model_call():
    env = make_topic_app()
    response = env.client.post('/topics/resolve', json={'text': 'Trust in Allah'})
    assert response.json['topics'][0]['verse_refs'] == INDEX['Trust in Allah']['verse_refs']
    env.post.assert_not_called()


@pytest.mark.parametrize('authenticated, limit', [(False, 10), (True, 150)])
def test_rate_limit_is_shared_with_tafsir_family_even_for_cache_hits(authenticated, limit):
    env = make_topic_app()
    headers = {'Authorization': 'Bearer offline'} if authenticated else {}
    for _ in range(limit):
        assert env.client.post('/topics/resolve', json={'text': 'Patience'}, headers=headers).status_code == 200
    result = env.client.post('/topics/resolve', json={'text': 'Patience'}, headers=headers)
    assert result.status_code == 429
    assert result.headers['Retry-After'] == '60'
    assert len(result.json['topics']) == 8
    key = 'offline-user' if authenticated else 'guest_127.0.0.1'
    assert len(env.namespace['USER_RATE_LIMITS'][key]) == limit
    env.post.assert_not_called()


def test_cache_expires_and_has_bounded_size():
    env = make_topic_app()
    env.clock.side_effect = None
    env.clock.return_value = 10
    env.post.return_value = model_response(VALID)
    env.client.post('/topics/resolve', json={'text': 'a life question'})
    env.clock.return_value = 3611
    env.client.post('/topics/resolve', json={'text': 'a life question'})
    assert env.post.call_count == 2
    cache = env.namespace['TOPIC_RESPONSE_CACHE']
    cache.update({f'fixture-{i}': (99999, {}) for i in range(255)})
    env.client.post('/topics/resolve', json={'text': 'another life question'})
    assert len(cache) == 256
