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

The 0.10 release candidate is `pretty-notebook==0.10.0rc2`. It includes current
settings/profiles, identities, checked publication, search/navigation, appearance
preferences and coordinated worker deployments. Candidate installation:

```sh
python -m pip uninstall pnbp
python -m pip install pretty-notebook==0.10.0rc2
```

The old stable release remains `pnbp==0.9.0` until the candidate exercise passes.
[0.10 release notes](docs/release-0.10.0.md) and
[versions/support](docs/versions.md) define the included scope. Hosted
documentation remains separate; tagged GitHub documentation is the release reference.

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
