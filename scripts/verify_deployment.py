#!/usr/bin/env python3
"""Read-only Cloud Run verification; never builds, deploys or changes traffic."""
import argparse
import json
import re
import subprocess
import sys


def gcloud_json(*args):
    return json.loads(subprocess.check_output(['gcloud', *args, '--format=json'], text=True))


def build_digest(project, build_id, image):
    build = gcloud_json('builds', 'describe', build_id, '--project', project)
    if build.get('status') != 'SUCCESS':
        raise ValueError(f"Build {build_id} is {build.get('status', 'unknown')}, not SUCCESS.")
    images = build.get('results', {}).get('images', [])
    matched = [entry.get('digest') for entry in images if entry.get('name') == image]
    if len(matched) != 1 or not matched[0] or not re.fullmatch(r'sha256:[a-f0-9]{64}', matched[0]):
        raise ValueError(f'Build {build_id} has no unambiguous digest for {image}.')
    return matched[0]


def verify(service, revision, digest, project, region, no_traffic=False):
    rev = gcloud_json('run', 'revisions', 'describe', revision, '--project', project, '--region', region)
    svc = gcloud_json('run', 'services', 'describe', service, '--project', project, '--region', region)
    status = rev.get('status', {})
    actual_revision = rev.get('metadata', {}).get('name')
    actual_digest = status.get('imageDigest', '').rsplit('@', 1)[-1]
    latest = svc.get('status', {}).get('latestReadyRevisionName', 'unknown')
    traffic = svc.get('status', {}).get('traffic', [])
    share = sum(target.get('percent', 0) or 0 for target in traffic if target.get('revisionName') == revision)
    conditions = status.get('conditions', [])
    ready = next((condition for condition in conditions if condition.get('type') == 'Ready'), {})
    failures = []
    for label, resource in (('Revision', rev), ('Service', svc)):
        generation = resource.get('metadata', {}).get('generation')
        if generation is not None and resource.get('status', {}).get('observedGeneration') != generation:
            failures.append(f'{label} reconciliation is incomplete: observedGeneration does not match generation.')
    if actual_revision != revision:
        failures.append(f'Requested revision {revision}; received {actual_revision}.')
    if actual_digest != digest:
        failures.append(f'Image digest mismatch: built {digest}, revision has {actual_digest or "none"}.')
    if ready.get('status') != 'True':
        reason = ready.get('reason', 'unknown')
        failures.append(f'Revision {revision} is not ready ({reason}): {ready.get("message", "no readiness message")}. A retired revision cannot be treated as latest.')
    active = next((condition for condition in conditions if condition.get('type') == 'Active'), {})
    if active.get('status') == 'False' and active.get('reason') == 'Retired':
        failures.append(f'Revision {revision} is retired and cannot serve traffic, even if Ready was previously true.')
    service_ready = next((c for c in svc.get('status', {}).get('conditions', []) if c.get('type') == 'Ready'), {})
    if service_ready.get('status') != 'True':
        failures.append(f'Service {service} is not ready: {service_ready.get("reason", "unknown")}.')
    expected_share = 0 if no_traffic else 100
    if share != expected_share:
        serving = ', '.join(f"{t.get('revisionName', 'unresolved')}={t.get('percent', 0) or 0}%" for t in traffic)
        failures.append(f'Actual traffic for {revision} is {share}%, expected {expected_share}%. Serving: {serving or "none"}. Traffic may be pinned to an older revision; latestReady={latest} is not proof of production traffic.')
    if no_traffic and not any(t.get('revisionName') == revision and t.get('tag') and t.get('url') for t in traffic):
        failures.append('The zero-traffic canary has no tagged URL; it may be retired. Keep an explicit canary tag.')
    if failures:
        raise ValueError('\n'.join(failures))
    mode = 'tagged zero-traffic canary' if no_traffic else 'production traffic'
    return f'Verified {revision}: digest={digest}, Ready=True, traffic={share}% ({mode}). Service URL: {svc.get("status", {}).get("url", "unknown")}'


def preflight(service, project, region):
    """Refuse a normal deploy unless traffic follows LATEST at 100%.

    A `--no-traffic` canary makes gcloud rewrite "100% LATEST" into a pin on the
    then-current revision, so the next normal deploy would build, create a 0% revision
    and only then fail. Catch that before building, and print the reviewed switch.
    """
    svc = gcloud_json('run', 'services', 'describe', service, '--project', project, '--region', region)
    traffic = svc.get('status', {}).get('traffic', [])
    latest = sum(t.get('percent', 0) or 0 for t in traffic if t.get('latestRevision'))
    if latest == 100:
        return f'Traffic follows LATEST at 100% for {service}; safe to deploy.'
    serving = ', '.join(
        f"{t.get('revisionName', 'LATEST')}={t.get('percent', 0) or 0}%" + (f" tag={t['tag']}" if t.get('tag') else '')
        for t in traffic)
    raise ValueError(
        f'Traffic for {service} is pinned ({serving or "none"}), probably by an earlier --no-traffic canary. '
        'A normal deploy would create a revision that serves 0%. Resolve it first with the reviewed switch:\n'
        f'  1. gcloud run services update-traffic {service} --project {project} --region {region} '
        '--to-revisions <REVIEWED_REVISION>=100 --remove-tags <CANARY_TAG>\n'
        '  2. verify that revision is serving, then\n'
        f'  3. gcloud run services update-traffic {service} --project {project} --region {region} --to-latest\n'
        '     (only once latestReadyRevisionName is the revision you want; a retired revision is skipped).')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build-digest')
    build.add_argument('--project', required=True); build.add_argument('--build-id', required=True); build.add_argument('--image', required=True)
    check = sub.add_parser('verify')
    for name in ('project', 'region', 'service', 'revision', 'digest'): check.add_argument('--' + name, required=True)
    check.add_argument('--no-traffic', action='store_true')
    pre = sub.add_parser('preflight')
    for name in ('project', 'region', 'service'): pre.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'build-digest': print(build_digest(args.project, args.build_id, args.image))
        elif args.command == 'preflight': print(preflight(args.service, args.project, args.region))
        else: print(verify(args.service, args.revision, args.digest, args.project, args.region, args.no_traffic))
    except (ValueError, KeyError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f'Deployment verification failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
