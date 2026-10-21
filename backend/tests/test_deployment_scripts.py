"""Run the actual entrypoints with a PATH-only gcloud stub; no cloud calls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]

STUB = r'''
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
path = Path(os.environ['DEPLOY_STUB_STATE'])
state = json.loads(path.read_text()) if path.exists() else {}
scenario = os.environ['DEPLOY_STUB_SCENARIO']
digest = 'sha256:' + 'a' * 64
def value(flag): return args[args.index(flag) + 1]
def save(): path.write_text(json.dumps(state))
def output(data): print(json.dumps(data))
if args[:2] == ['auth', 'list']:
    print('offline@example.test')
elif args[:2] == ['builds', 'submit']:
    state['image'] = value('--tag'); save(); print('offline-build')
elif args[:2] == ['builds', 'describe']:
    output({'status': 'SUCCESS', 'results': {'images': [{'name': state['image'], 'digest': digest}]}})
elif args[:2] == ['run', 'deploy']:
    state.update(service=args[2], revision=args[2] + '-' + value('--revision-suffix'),
                 no_traffic='--no-traffic' in args, image_arg=value('--image'), deploy_args=args)
    if '--tag' in args: state['tag'] = value('--tag')
    save(); print('old-revision' if scenario == 'wrong-latest' else state['revision'])
elif args[:3] == ['run', 'revisions', 'describe']:
    conditions = [{'type': 'Ready', 'status': 'False' if scenario == 'not-ready' else 'True', 'reason': 'Deploying'}]
    if scenario == 'retired': conditions.append({'type': 'Active', 'status': 'False', 'reason': 'Retired'})
    output({'metadata': {'name': state['revision'], 'generation': 1},
            'status': {'observedGeneration': 0 if scenario == 'reconciling' else 1,
                       'conditions': conditions, 'imageDigest': 'gcr.io/image@' + ('sha256:' + 'b' * 64 if scenario == 'wrong-digest' else digest)}})
elif args[:3] == ['run', 'services', 'describe'] and 'revision' not in state:
    # Preflight, before anything is built or deployed.
    if scenario == 'pre-pinned':
        traffic = [{'revisionName': 'old-revision', 'percent': 100},
                   {'revisionName': 'canary-revision', 'percent': 0, 'tag': 'r-canary', 'url': 'https://offline.invalid/c'}]
    else:
        traffic = [{'revisionName': 'old-revision', 'percent': 100, 'latestRevision': True}]
    output({'status': {'traffic': traffic, 'latestReadyRevisionName': 'old-revision'}})
elif args[:3] == ['run', 'services', 'describe']:
    percent = 0 if state['no_traffic'] or scenario in ['pinned', 'canary-latest'] else 100
    if scenario == 'unexpected-canary-traffic': percent = 100
    traffic = [{'revisionName': 'old-revision', 'percent': 100 - percent}, {'revisionName': state['revision'], 'percent': percent}]
    if state.get('tag'): traffic[-1].update(tag=state['tag'], url='https://offline.invalid/tag')
    output({'metadata': {'generation': 1}, 'status': {'observedGeneration': 1,
       'conditions': [{'type': 'Ready', 'status': 'True'}], 'traffic': traffic,
       'latestReadyRevisionName': 'old-revision' if scenario == 'old-latest-good-traffic' else state['revision'],
       'url': 'https://offline.invalid'}})
else:
    sys.exit('Unexpected stub command: ' + repr(args))
'''


@pytest.mark.parametrize('service', ['backend', 'frontend'])
@pytest.mark.parametrize('scenario,flag,expected', [
    ('success', None, 'traffic=100%'), ('success', '--no-traffic', 'zero-traffic canary'),
    ('pinned', None, 'Traffic may be pinned'), ('canary-latest', None, 'latestReady='),
    ('wrong-latest', None, 'expected created revision'), ('wrong-digest', None, 'Image digest mismatch'),
    ('retired', None, 'retired'), ('not-ready', None, 'not ready'),
    ('reconciling', None, 'reconciliation is incomplete'),
    ('unexpected-canary-traffic', '--no-traffic', 'expected 0%'),
    ('old-latest-good-traffic', None, 'traffic=100%'),
    ('pre-pinned', None, 'is pinned'),
])
def test_entrypoints_verify_created_digest_readiness_and_actual_traffic(tmp_path, service, scenario, flag, expected):
    binary = tmp_path / 'gcloud'
    binary.write_text(f'#!{sys.executable}\n' + STUB); binary.chmod(0o755)
    state = tmp_path / 'state.json'
    env = {**os.environ, 'PATH': str(tmp_path) + os.pathsep + os.environ['PATH'],
           'DEPLOY_STUB_STATE': str(state), 'DEPLOY_STUB_SCENARIO': scenario}
    command = ['bash', str(ROOT / f'deploy-{service}.sh')]
    if flag: command.append(flag)
    result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=15)
    successful = scenario in ('success', 'old-latest-good-traffic')
    assert (result.returncode == 0) == successful, result.stdout + result.stderr
    assert expected in result.stdout + result.stderr
    if scenario == 'pre-pinned':
        # Refused before building: no image was submitted and nothing was deployed.
        assert not state.exists() or 'image' not in json.loads(state.read_text())
        assert '--to-revisions' in result.stderr and '--to-latest' in result.stderr
    if state.exists() and 'image_arg' in json.loads(state.read_text()):
        deployed = json.loads(state.read_text())
        assert '@sha256:' in deployed['image_arg']
        args = deployed['deploy_args']
        if service == 'frontend':
            assert '--set-env-vars' not in args and '--set-secrets' not in args
        else:
            pairs = lambda flag: dict(pair.split('=', 1) for pair in args[args.index(flag) + 1].split(','))
            assert pairs('--set-env-vars') == {
                'FIREBASE_PROJECT': 'tafsir-simplified-6b262',
                'GCP_INFRASTRUCTURE_PROJECT': 'tafsir-simplified', 'GCP_LOCATION': 'us-central1',
                'GEMINI_API_LOCATION': 'global', 'GEMINI_MODEL_ID': 'gemini-3.8-flash',
                'GEMINI_LITE_MODEL_ID': 'gemini-3.5-flash-lite',
                'GCS_BUCKET_NAME': 'tafsir-simplified-sources',
                'FIREBASE_SECRET_FULL_PATH': 'projects/612616741510/secrets/firebase-sa-key/versions/latest',
            }
            assert pairs('--set-secrets') == {
                'ADMIN_SECRET': 'admin-secret:latest',
                'REFLECTION_ENCRYPTION_SECRET': 'reflection-encryption-key:latest',
            }
