# 0.9 release handoff

## Current work

- DOC-01 merged to protected `main` through PR #47 at `202f7d7555072af0d365d315e8b73b55458279b3`.
- Branch: `build/dep-01b-web-lock`, based on that `main` commit. It carries
  the DEP-01B hash lock and web CI install change.
- PR #47 removed unsupported macOS URL-handler setup instructions,
  documents the one-notebook `--prune` boundary, retains the Bootstrap Icons
  license notice, and pins the experimental web requirements snapshot to the
  published `pnbp==0.9.0rc1` package.
- This pass updates the README and package/CLI entry points to identify the
  published RC, pin the install example, and make the experimental web boundary
  visible. It also changes the RC notes from a pre-publication plan to a record
  of the published candidate and its release workflow.

## Verified release boundary

- PyPI has the `pnbp` 0.9.0rc1 wheel and source distribution, uploaded on
  September 26, 2026. GitHub has the `v0.9.0rc1` pre-release, and its release
  workflow completed successfully.
- The 0.9.0rc1 package exposes the `pnbp` Python library and CLI and requires
  Python 3.11 or newer. `apps/web` remains experimental and unsupported for
  public deployment. The macOS URL handlers are unsupported.
- One notebook must own the complete page namespace before `--prune` is used.
  Shared ownership across independent notebooks/users is not a supported 0.9
  contract.

## Remaining separate gates

- DEP-01B: the 47-package hash lock is in `apps/web/requirements.lock` for
  Linux x86_64 CPython 3.11 and 3.14. The web CI job installs it with hashes
  and wheels only before running the integration suite. Public deployment
  remains gated on web deployment safety.
- Web deployment safety and any decision to support public deployment remain
  separate from the published package release.
- REL-02: exercise the candidate and decide final 0.9.0 release readiness.

## Verification

- PR #47 passed Python 3.11, Python 3.14, distribution, and web API checks,
  had no review comments, and merged through branch protection.
- This pass checks the documentation diff for whitespace errors and verifies
  the changed relative links and release boundary text. No code tests were
  rerun for documentation-only edits.

## DEP-01B follow-up (October 1, 2026)

- Generated `apps/web/requirements.lock` from the RC1-pinned snapshot using
  uv 0.12.19. Linux x86_64 resolutions for CPython 3.11 and 3.14 produced
  byte-identical lock contents after removing uv's annotations and header.
- `pip download --require-hashes --only-binary=:all:` fetched and verified all
  locked Linux wheels for each Python version. The web CI install now uses the
  lock; its stacked PR #48 passed all five checks before being superseded by a
  clean branch based on merged `main`. Confirm the replacement PR checks pass.
- REL-02 candidate exercise and the separate web deployment safety decision
  remain open. Do not treat the lock alone as public deployment approval.
