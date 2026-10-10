# Pretty-Notebook

A Python toolkit for interconnected Markdown notebooks. The repository also
contains a FastAPI publisher with a constrained public-deployment profile.

The `0.9.0` release supports the `pnbp` Python package and its `pnbp`
command-line interface on Python 3.11 or newer:

```bash
python -m pip install --upgrade pip
python -m pip install pnbp==0.9.0
```

The repository supports the `apps/web` publisher as one Gunicorn instance with up to four workers,
one local SQLite database and one owning notebook behind a TLS reverse proxy. Read the
deployment contract and security boundaries before exposing it publicly. The
macOS URL handlers remain unsupported.

[Documentation index](docs/index.md) · [Workflow tutorial](docs/tutorials.md) · [0.9.0 release notes](docs/release-0.9.0.md) · [Web deployment](docs/web.md) · [Development roadmap](docs/roadmap.md)

The current checkout includes features targeting **0.10 development**, while
package metadata prepares `pretty-notebook==0.10.0.dev0`. Use an editable
checkout for current settings/profiles, identities, checked moves/publication,
field/tag search, navigation and favicon management. Those APIs are not promised
by the published 0.9.0 wheel. [Versions and support](docs/versions.md) defines the
distinction; [building the documentation](docs/building.md) checks the same
canonical Markdown with strict references, emitted HTML links and runnable local
examples. Hosted documentation publication remains pending separately.

New code uses `from pretty_notebook import Notebook, Note`; existing `pnbp`
imports and the `pnbp` executable remain compatible. See the
[package migration](docs/package-migration.md) before upgrading old installations.

```mermaid
graph BT
	id1[(Notebook)]
	id2[(Note)] --> id1
	Link --> id2
	Url --> id2
	CodeBlock --> id2
	Tag --> id2
```

<p align=center>
  <img src=https://raw.githubusercontent.com/outside-labs/Pretty-Notebook/main/docs/IMG_pnbp.png alt=Pretty-Notebook width=200>
</p>
