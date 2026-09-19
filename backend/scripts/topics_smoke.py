#!/usr/bin/env python3
"""Offline manual /topics/resolve smoke: five phrases, fake lite call, no credentials.

Run from repo root: python3 backend/scripts/topics_smoke.py
This exercises the real Flask route with an in-process client. It never contacts
production or Gemini; results demonstrate the contract, not live model quality.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.tests.topic_harness import make_topic_app, model_response


def main():
    samples = [
        ('patience during hardship', 'Patience'),
        ('how can I seek forgiveness?', 'Forgiveness'),
        ('being kinder to my family', 'Family'),
        ('I feel uncertain about the future', 'Trust in Allah'),
        ('help me pick a new laptop', None),
    ]
    env = make_topic_app()
    for phrase, name in samples:
        mapping = {'topics': [{'name': name, 'confidence': 0.9}]} if name else {'topics': []}
        env.post.return_value = model_response(mapping)
        response = env.client.post('/topics/resolve', json={'text': phrase})
        assert response.status_code == 200
        topics = response.json['topics']
        assert len(topics) == (1 if name else 8)
        print(f'{phrase} -> {response.status_code}: ' + '; '.join(
            f"{topic['name']} [{', '.join(topic['verse_refs'])}]" for topic in topics))
    assert env.post.call_count == 5
    print('PASS: 5 offline endpoint requests; 5 fake lite calls; 0 live calls.')


if __name__ == '__main__':
    main()
