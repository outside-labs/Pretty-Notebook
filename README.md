# Pretty-Notebook

A Python toolkit for interconnected Markdown notebooks. The repository also
contains a FastAPI publisher with a constrained public-deployment profile.

The published `0.9.0rc1` release supports the `pnbp` Python package and its
`pnbp` command-line interface on Python 3.11 or newer. Install the candidate
explicitly with `python -m pip install pnbp==0.9.0rc1`.
Current `main` supports the `apps/web` publisher only as a single-worker,
single-SQLite, single-notebook deployment behind a TLS reverse proxy. Read the
deployment contract and security boundaries before exposing it publicly. The
macOS URL handlers remain unsupported.

[Package documentation](docs/pnbp.md) · [0.9.0rc1 release notes](docs/release-0.9.0rc1.md) · [Web deployment](docs/web.md)

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
