# pnbp 0.9.0rc1

`0.9.0rc1` is the release candidate for the Pretty Notebook `pnbp` package. It focuses on data safety, deterministic lookup and matching, publication failure handling, CLI correctness, configuration behavior, and regression coverage before the final `0.9.0` release.

## Installation

Release candidates are pre-releases. After the candidate is published, install this exact build with:

```sh
python -m pip install pnbp==0.9.0rc1
```

Python 3.11 or newer is required.

## Migration notes

- The supported command-line entry point is `pnbp` with subcommands. Older `nb-*` / `nbn-*` command entry points are not the 0.9 interface.
- Exact note lookup is preferred. Approximate mutation targets require explicit fuzzy acceptance where the command supports it.
- `PNBP_SETTINGS=off` disables `pnbp_settings.json` loading even when that file exists.
- `pnbp commit-settings` targets the configured remote by default; use `--local` explicitly for the local service.
- Cleanup commands revalidate destructive targets at execution time and refuse destructive cleanup while notes have unsaved changes.

## Candidate safety and correctness work

The RC incorporates regression-backed work for:

- non-publishing pull-request CI and package smoke checks;
- non-mutating note inspection/rendering and failure-safe persistence;
- transactional task settlement;
- exact public-note eligibility, publication preflight, and failure-aware synchronization;
- contained code extraction and notebook-scoped Git automation;
- literal-code-safe rendering;
- exact-first lookup, stable component semantics, and correct multi-value query behavior;
- non-recursive collection dispatch, restored collection commands, and safer cleanup/empty-note operations;
- configuration-off behavior, generated defaults, explicit local/remote selection, and redacted token refresh output.

## Known unsupported surfaces

The installable `pnbp` package is the scope of this release candidate. These repository surfaces are **not** supported production features in `0.9.0rc1`:

- `apps/web` is experimental and is not supported for public deployment until the separate web deployment safety gate is completed.
- `pnano.app` and `ppnbp.app` protocol handlers are experimental/unsupported.
- Publication ownership across multiple independent notebooks/users is not yet a supported contract; do not share one destructive prune namespace between them.

## Candidate verification before publication

Before publishing the release candidate, the release workflow must verify that the Git tag is exactly `v0.9.0rc1`, run warnings-as-errors compilation, the release-blocking Ruff rules, and the regression suite, build the source and wheel distributions, run strict Twine metadata checks, install the built wheel in a fresh environment, run `pip check`, import `pnbp`, run `pnbp --help`, and perform the Notebook smoke test. Publishing remains a separate protected-environment job using PyPI trusted publishing.

The final `0.9.0` release should follow candidate exercise/feedback plus the remaining final-release documentation, license-notice, and support-status decisions.
