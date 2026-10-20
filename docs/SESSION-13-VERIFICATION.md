# Session 13 verification notes

## Unit 2 dependencies and proxy assumptions

Next **15.5.27** and Capacitor CLI/core/iOS **8.5.1** are pinned with a regenerated lockfile. Vendor sources: [Next release](https://github.com/vercel/next.js/releases/tag/v15.5.27), [Capacitor advisory](https://github.com/ionic-team/capacitor/security/advisories/GHSA-rvm3-566m-v7fv). `npx cap sync ios` succeeded. Swift Package.swift and Package.resolved use 8.5.1, upstream tag `6afa7424fd2fcd8ca1e577478e8a00af284b7e82`; no native build or distribution occurred. Runtime Docker dependencies are copied from the pruned builder installation; Node 24 matches local verification and Capacitor's engine requirement.

ProxyFix trusts **one rightmost XFF value**, only when Cloud Run sets K_SERVICE. It does not trust forwarded host/port/prefix. This is scoped to the current direct run.app ingress, without a separately configured external Application Load Balancer. [Cloud Run functions header documentation](https://docs.cloud.google.com/functions/docs/reference/headers) describes the ordered client/proxy chain; [Werkzeug](https://werkzeug.palletsprojects.com/en/stable/middleware/proxy_fix/) requires an explicit trusted hop count. The count is an inference from this direct-ingress topology, **not an explicit numerical guarantee in the linked Google page**. The spoofed-left-prefix regression proves rightmost selection offline. Claude should verify the observed platform-appended hop during the deployment smoke test, and reassess before adding a proxy; never switch to leftmost selection. No live request was made here.

`npm audit --omit=dev --json` after the upgrade: **16 affected packages** (3 critical, 8 high, 5 moderate). Next has no remaining direct advisory in this result; its reported moderate status is inherited from PostCSS. Capacitor CLI's moderate status is inherited from xcode. These are not claims of application exploitability. Remaining paths and advisory-specific analysis are in the [audit appendix](AUDIT-2026-10-GPT6.md#dependency-findings-and-per-advisory-reachability). No forced major upgrades or transitive overrides were introduced.

| Remaining npm package | Severity | Context |
|---|---|---|
| @capacitor/cli | moderate | Inherited xcode/uuid tooling; not the patched native-origin flaw. |
| @grpc/grpc-js | high | Firebase transitive; no untrusted gRPC server endpoint. |
| @protobufjs/utf8 | moderate | Tooling or transitive dependency; advisory-specific reachability remains as assessed in the audit appendix. |
| @xmldom/xmldom | high | Tooling or transitive dependency; advisory-specific reachability remains as assessed in the audit appendix. |
| brace-expansion | high | Tooling or transitive dependency; advisory-specific reachability remains as assessed in the audit appendix. |
| minimatch | high | Tooling or transitive dependency; advisory-specific reachability remains as assessed in the audit appendix. |
| nanoid | high | Tooling or transitive dependency; advisory-specific reachability remains as assessed in the audit appendix. |
| next | moderate | Inherited PostCSS build-time source map advisories; no reader CSS compilation. |
| postcss | high | Build-time local CSS; no reader-controlled source-map compilation. |
| protobufjs | critical | Firebase transport dependency; no schema/descriptor upload or reflection interface. |
| sharp | high | Fixed local PNG logo; no upload or remote image sources. |
| source-map-js | high | Tooling or transitive dependency; advisory-specific reachability remains as assessed in the audit appendix. |
| tar | critical | Tooling or transitive dependency; advisory-specific reachability remains as assessed in the audit appendix. |
| uuid | moderate | Tooling or transitive dependency; advisory-specific reachability remains as assessed in the audit appendix. |
| websocket-driver | critical | Firebase transitive; no app WebSocket frame server. |
| xcode | moderate | Tooling or transitive dependency; advisory-specific reachability remains as assessed in the audit appendix. |

`pip-audit` ran from `/tmp/tadabbur-audit-venv`, resolving backend/requirements.txt without installing into the application venv: **20 advisory entries in 5 packages** (Flask 3.0.3: 2; flask-cors 4.0.0: 10; requests 2.32.3: 4; cryptography 49.0.0: 2; protobuf 4.25.9: 2). Aliases can duplicate entries; see the audit's per-advisory table. Relevant absent preconditions remain cookie-session use, differing per-path CORS rules, reader-supplied outbound URLs/zipped paths, PKCS7 decryption, and reader-controlled protobuf Any/descriptor parsing. Python 3.14 resolver output is not a production Python 3.11 container SBOM. Python upgrades remain separate compatibility work; no claim of a clean dependency scan.

Enforced frontend headers: X-Frame-Options DENY, CSP frame-ancestors none, strict-origin-when-cross-origin referrers, one-year HSTS. The fuller CSP is **Report-Only**, with no collection endpoint configured: self; Next inline hydration/styles; Google gstatic/google.com/recaptcha.net/apis.google.com; googleapis.com; firebaseapp.com/firebaseio.com; fonts.googleapis.com/fonts.gstatic.com; configured Cloud Run backend; data images. Review console violations before enforcement or adding a report collector.

## Unit 6 deployment and boundary verification

Both deploy entrypoints source `scripts/deploy-common.sh`, build a uniquely tagged image, take its digest from the exact successful Cloud Build result, deploy by that immutable digest with an explicit revision suffix, capture latestCreatedRevisionName, and require it to equal that explicit name. `scripts/verify_deployment.py` reads the named revision and observed service status. It checks the image digest, readiness/reconciliation, retired state, and resolved status.traffic percentages. A normal deployment requires the created revision to receive 100%; it fails with the serving revisions/percentages when traffic is pinned elsewhere. It never treats latestReady as evidence of production traffic and never changes traffic to repair a failure.

An intentional canary uses `bash deploy-backend.sh --no-traffic` or `bash deploy-frontend.sh --no-traffic`; the script creates a unique tag, verifies its tagged URL and 0% share, and still requires the named revision to be ready with the correct digest. Scripts do not change the caller's default gcloud project or start an interactive login. Claude owns execution. **No real deploy command was run.** The 22 entrypoint tests replace gcloud on PATH and use local JSON fixtures, including macOS Bash's empty-array behavior.

Primary API references: [Cloud Run revision status/imageDigest/reconciliation](https://docs.cloud.google.com/run/docs/reference/rest/v1/namespaces.revisions), [Cloud Build results](https://docs.cloud.google.com/build/docs/api/reference/rest/v1/projects.builds#results), [Cloud Run traffic migration](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration). The maintained annotation-count legacy seed uses the SDK's supported existing-transaction aggregation parameter; see [Firestore aggregation API](https://docs.cloud.google.com/firestore/docs/reference/rest/v1/projects.databases.documents/runAggregationQuery).

The real boundary harness retains Flask route decorators, auth/admin/debug wrappers, parser, exact profile/version cache reads and share snapshot helpers while replacing clients. It exercises guest and signed-in cache hits through the actual /tafsir handler, canonical syntax equivalence, invalid/ambiguous references, exact profile misses, old pipeline rejection, public historical snapshots, ignored caller-provided share bodies, deletion markers, and required/debug/cron denials. Operational admin denials are covered by the Unit 2 fixture. No application startup, Firebase initialization, GCS retrieval, credential loading or model generation occurs in these fixtures.

Verification also found and closed residual edges: diagnostic generation no longer writes to the reader cache; share requests validate text/reference types before lookup; served tafsir suggestions are canonical references; short collection names cannot masquerade as narrators; a separate scholarly-source delimiter prevents inheriting the preceding tafsir's attribution; the migration refuses to re-encrypt unreadable legacy ciphertext with a possibly wrong key; feedback mail failures no longer print recipient-bearing exception messages; onboarding completions carry the auth generation, including A/B/A switches; persisted answer queries and share IDs retain answer ownership. Actual search/share handler tests use deferred responses to verify timer/loading and pending-share ownership.

Final offline checks:

- `backend/venv/bin/python -m pytest backend/tests -q`: **571 passed**.
- `cd frontend` then `node --test tests/*.test.*`: **18 passed**.
- Frontend `npm run build`: **15/15**, no `window is not defined`.
- `bash -n deploy-backend.sh deploy-frontend.sh scripts/deploy-common.sh` and `git diff --check`: pass.

Limits and handoff prerequisites: no live Firestore/emulator integration, paid golden canary, native iOS build, Docker image build, account erasure, migration, secret creation or deployment was performed. Claude must create the encryption secret, review/dry-run the migration, perform the paid pipeline-17.0 canary, verify the proxy-hop topology, set budget/quota controls, and own deployment. Ahmed must approve privacy/contact text, public-share policy and deletion-marker retention. Existing saved/shared snapshots predate the attribution fix. The 0.80 wording threshold and Firestore TTL policy remain unchanged. LOG-09/10 remain deferred behind Iman gating, PERF-03 remains deferred at current traffic, and OPS-01 cloud protection is Claude's completed work with a restore drill/runbook still outstanding.
