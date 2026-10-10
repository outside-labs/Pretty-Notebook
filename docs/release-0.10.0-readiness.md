# Pretty Notebook 0.10 readiness

The candidate is `pretty-notebook==0.10.0rc1`, selected by `v0.10.0rc1`.
The `pnbp` compatibility distribution is built and checked alongside it but is
uploaded only for the final release.

Before final publication:

1. Verify passing library, web/coverage, JavaScript, deployment and strict docs CI.
2. Install the actual candidate from PyPI in fresh Python 3.11 and 3.14 environments.
3. Verify canonical/legacy import identity, CLI/deployment resources and dependency consistency.
4. Run `scripts/exercise_release.py 0.10.0rc1` against fresh synthetic notes.
5. Save synthetic notes with the published 0.9 wheel, uninstall it, install the
   candidate, then exercise legacy settings migration, identity-preserving rename,
   backlink repair, pending save, routes, search/navigation and local publication.
6. Check old-server state restore, legacy-client behavior, hash/image updates and
   worker coordination using the existing web integration and deployment checks.

Preserve source and data backups. A final GO requires no unresolved data-loss,
migration or publication-conflict defect. Hosted documentation and actual VPS
activation are deferred; tagged GitHub documentation provides the release reference.

Candidate and final evidence will be recorded here after their exercises pass.
