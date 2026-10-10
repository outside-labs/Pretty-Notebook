# Pretty Notebook 0.10 readiness

The candidate is `pretty-notebook==0.10.0rc2`, selected by `v0.10.0rc2`.
The `pnbp` compatibility distribution is built and checked alongside it but is
uploaded only for the final release.

Before final publication:

1. Verify passing library, web/coverage, JavaScript, deployment and strict docs CI.
2. Install the actual candidate from PyPI in fresh Python 3.11 and 3.14 environments.
3. Verify canonical/legacy import identity, CLI/deployment resources and dependency consistency.
4. Run `scripts/exercise_release.py 0.10.0rc2` against fresh synthetic notes.
5. Save synthetic notes with the published 0.9 wheel, uninstall it, install the
   candidate, then exercise legacy settings migration, identity-preserving rename,
   backlink repair, pending save, routes, search/navigation and local publication.
6. Check old-server state restore, legacy-client behavior, hash/image updates and
   worker coordination using the existing web integration and deployment checks.

Preserve source and data backups. A final GO requires no unresolved data-loss,
migration or publication-conflict defect. Hosted documentation and actual VPS
activation are deferred; tagged GitHub documentation provides the release reference.

## Current evidence and publication gate

- Candidate source: `b66c671730cd20a4b5f0994c95651dffe6263496`, tag `v0.10.0rc2`.
- Library, web/coverage, JavaScript, packaging, deployment and strict docs CI
  passed before candidate publication.
- The [rc2 release build](https://github.com/outside-labs/Pretty-Notebook/actions/runs/38091094329)
  passed on supported Python 3.14, including both distribution builds, strict
  metadata/ownership checks and the installed-wheel notebook exercise.
- The earlier rc1 build stopped on the inherited Python 3.12 deployment check;
  [the correction](https://github.com/outside-labs/Pretty-Notebook/pull/165)
  moved release builds to supported Python 3.14. No rc1 packages were uploaded.
- The rc2 upload was rejected by PyPI with HTTP 400, reporting that a non-user
  identity cannot create the requested project. Package metadata correctly names
  `pretty-notebook`; the saved pending publisher fields must be verified against
  `outside-labs`, `Pretty-Notebook`, `release.yaml`, and `pypi`.
- Both prepared final `0.10.0` wheel/source distributions pass strict metadata
  and ownership checks. The local notebook migration/edit/route/search exercise
  passes for the prepared final library.

**GO remains pending.** Resolve the publisher registration, rerun only the failed
rc2 upload, then exercise the actual PyPI candidate on Python 3.11 and 3.14,
including the prepared notebooks saved by the published 0.9 wheel. Final tagging
and upload follow that evidence and passing final-version CI. Hosted docs and
live VPS activation remain separate operations.
