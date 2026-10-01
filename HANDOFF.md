# Pretty Notebook 0.9 handoff (October 1, 2026)

## Completed on protected `main`

- DOC-01 and LICENSE-01 merged through PR #47 (`202f7d7555072af0d365d315e8b73b55458279b3`). The documentation identifies the published RC, removes unsupported macOS URL-handler setup, explains the single-notebook `--prune` boundary, and retains the Bootstrap Icons MIT notice.
- DEP-01B merged through PR #49 (`724dcead955ae53f904ed55267d355e10832098c`). `apps/web/requirements.lock` pins 47 packages with hashes for Linux x86_64 CPython 3.11 and 3.14. Web CI installs only hash-locked wheels before running integration tests.
- PR #49 and the post-merge `main` run passed Python 3.11, Python 3.14, distribution, and both web API checks. The squash commit is `build(web): lock deployment dependencies with hashes`.
- Project #1 contains PR #49 as a Done Web deployment item; all 25 current Project items are Done. There are no open repository issues. The remaining decisions below have not yet been made into separate Project issues.

## Published candidate and scope

- GitHub prerelease `v0.9.0rc1` and PyPI `pnbp==0.9.0rc1` were published September 26, 2026. The release workflow completed successfully.
- The supported candidate is the `pnbp` Python library and CLI on Python 3.11 or newer. `apps/web` remains experimental and unsupported for public deployment; `pnano.app` and `ppnbp.app` URL handlers are unsupported.
- A single notebook must own the complete server page namespace before `--prune` is used. Shared ownership across independent notebooks or users is not a supported 0.9 contract.
- The web lock covers the two verified Linux targets. Other deployment platforms and Python versions have not been verified against it.

## Next gates

1. REL-02: exercise the published RC against representative notebooks and workflows, collect feedback, fix any release-blocking defects through protected PRs, and decide whether `0.9.0` is ready.
2. Final package release, after that decision: update the package version and final notes, review the tag/version guard and built artifacts, then publish the final GitHub Release and PyPI package with explicit release authorization.
3. Separately decide the support scope for public web deployment, multi-notebook publication ownership (PUB-04), and macOS URL handlers (APP-01). The completed lock does not approve public web deployment.

Use Conventional Commit subjects for future commits and PRs. Keep protected checks and review comments resolved before merging. Do not infer final-release authorization from the RC publication.
