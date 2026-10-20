#!/usr/bin/env python3
"""Offline-reviewable migration. Dry run by default; never imports the cloud-starting app.

Owner runs after provisioning REFLECTION_ENCRYPTION_SECRET. --apply is explicit.
Each update carries the snapshot update-time precondition; reruns skip v1 fields.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
import hmac
import os

from cryptography.fernet import Fernet

PREFIX = 'fernet:v1:'
COLLECTIONS = ('annotations', 'iman_daily_logs', 'iman_struggles',
               'iman_weekly_digests', 'iman_daily_insights', 'iman_correlation_narratives')
TEXT_FIELDS = {
    'annotations': ('content', 'highlighted_text'),
    'iman_weekly_digests': ('opening', 'weekly_story', 'strength_noticed', 'correlation_insight', 'gentle_attention', 'closing'),
    'iman_daily_insights': ('observation', 'correlation', 'encouragement', 'strain_note'),
    'iman_correlation_narratives': ('narrative', 'key_insight'),
}


def migrate_fields(data, collection, cipher):
    result = deepcopy(data)

    def encrypt(mapping, key):
        value = mapping.get(key)
        if not isinstance(value, str) or not value or value.startswith(PREFIX):
            return
        try:
            plaintext = cipher.decrypt(value.encode()).decode()
        except Exception:
            plaintext = value
        mapping[key] = PREFIX + cipher.encrypt(plaintext.encode()).decode()

    for key in TEXT_FIELDS.get(collection, ()):
        encrypt(result, key)
    if collection == 'iman_daily_logs':
        for note in result.get('heart_notes', []): encrypt(note, 'text')
        for reflection in result.get('struggle_reflections', {}).values(): encrypt(reflection, 'text')
    if collection == 'iman_struggles':
        for excerpt in result.get('guidance_excerpts', []): encrypt(excerpt, 'text')
    if collection == 'iman_weekly_digests' and isinstance(result.get('verse_to_carry'), dict):
        encrypt(result['verse_to_carry'], 'text')
        encrypt(result['verse_to_carry'], 'why')
    return {key: value for key, value in result.items() if value != data.get(key)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, help='Firebase project containing the default user database')
    parser.add_argument('--apply', action='store_true', help='Write with update-time preconditions; default is dry run')
    args = parser.parse_args()
    secret = os.environ.get('REFLECTION_ENCRYPTION_SECRET')
    if not secret:
        parser.error('REFLECTION_ENCRYPTION_SECRET must be configured')
    from google.cloud import firestore
    from google.cloud.firestore_v1 import LastUpdateOption
    db = firestore.Client(project=args.project, database='(default)')
    changed = written = 0
    for user in db.collection('users').list_documents():
        key = hmac.new(secret.encode(), user.id.encode(), hashlib.sha256).digest()
        cipher = Fernet(base64.urlsafe_b64encode(key))
        for collection in COLLECTIONS:
            for doc in user.collection(collection).stream():
                updates = migrate_fields(doc.to_dict(), collection, cipher)
                if updates:
                    changed += 1
                    if args.apply:
                        doc.reference.update(updates, option=LastUpdateOption(doc.update_time))
                        written += 1
    print(f'mode={"apply" if args.apply else "dry-run"} changed_documents={changed} written_documents={written}')


if __name__ == '__main__':
    main()
