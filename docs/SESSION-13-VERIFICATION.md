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
