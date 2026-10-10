# Pretty Notebook package

Pretty Notebook is a Python library and command-line interface for interconnected
Markdown notebooks. A notebook is an existing directory of Markdown files;
a note is one source file. Wiki links, tags, code blocks and URLs have explicit
models, while ordinary Markdown remains the authoritative content.

## Choose a version

The published `pnbp==0.9.0` package runs on Python 3.11 or newer:

```bash
python -m pip install pnbp==0.9.0
pnbp --help
```

The current checkout contains features targeting **0.10 development**. Its
package metadata prepares `pretty-notebook==0.10.0.dev0`. See the
[package migration](package-migration.md) for the canonical import and compatibility. Do not
assume development APIs exist in the published 0.9.0 wheel. See
[versions and support](versions.md) and the [0.9.0 release notes](release-0.9.0.md).

For development features, use a full checkout and install it locally:

```bash
git clone https://github.com/outside-labs/Pretty-Notebook.git
cd Pretty-Notebook
python -m venv .venv
.venv/bin/python -m pip install --editable .
```

On Windows, use `.venv\Scripts\python.exe` for the installation command.

## First notebook and existing notebooks

Follow the [notebook workflow tutorial](tutorials.md) for a temporary notebook,
initialization, pending edits, checked renames, search and navigation. Its local
examples are executed by the documentation build.

```python
from pretty_notebook import Notebook

nb = Notebook.open("~/notes", settings={"NOTE_NESTED": "recurs"})
note = nb.get("guides/overview", fuzzy=False)
```

The path must already exist. Opening reads files without prompting or creating
configuration. Initialize deliberately with `pnbp init PATH`; see the canonical
[settings and profile guide](settings.md) for precedence, migration and credentials.
`Notebook()` continues to use `NOTE_PATH` for existing environment-based setups.

## Continue by topic

- [Note commands and pending edits](editing.md): add/edit, empty bodies, saves and recovery drafts.
- [Models and methods](pnbp_models.md) and [generated API reference](reference.md): public imports and signatures.
- [Local search](local-search.md), [navigation](navigation.md) and [links](links.md): read-only projections and explicit traversal.
- [Stable identities](identities.md) and [publication routes](routes.md): identity, source paths and URLs remain separate.
- [Checked publishing](checked-publishing.md): dry-run plans, ETags, retries and explicit pruning.
- [Web deployment](web.md): separate application, bootstrap, durable state and the supported one-worker profile.

The macOS URL handlers are [unsupported](pnano.md). The FastAPI app and its
optional dependencies are absent from the `pnbp` wheel.
