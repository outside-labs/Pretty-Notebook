# Building the documentation

The Markdown files in `docs/` are the canonical documentation. Sphinx and MyST
render those same files; generated HTML and doctrees stay in the ignored
`docs/_build/` directory. The development roadmap remains in GitHub Markdown.

The pinned build tools require Python 3.12 or newer. This documentation-only
requirement does not change the package's Python 3.11 runtime support. From a
fresh checkout at the repository root:

```bash
python3.14 -m venv .venv-docs
.venv-docs/bin/python -m pip install --upgrade pip
.venv-docs/bin/python -m pip install --editable . --requirement docs/requirements.txt
.venv-docs/bin/python -m pip check
.venv-docs/bin/python -m sphinx -b html -n -W --keep-going -E docs docs/_build/html
```

On Windows, use `.venv-docs\Scripts\python.exe` for the same commands.
Open `docs/_build/html/index.html` after the build. Repeat the final command
after edits. `-E` rebuilds the environment, `-n` checks references, and `-W`
makes warnings fail the build. API reference imports use this checkout's
`src/` directory, while CLI help comes from the actual Click command registry
without running commands.

The documentation CI workflow installs only the package and declared docs
requirements, checks dependency compatibility, then runs that strict build.
Add pages to the index's toctree and use local Markdown links between pages;
MyST resolves and checks their heading fragments. Avoid suppressing warnings
to hide missing targets or incorrect public imports.

The prepared `.readthedocs.yaml` uses the same sources, requirements and
warnings-as-errors policy. Hosted project activation, domain configuration and
publication remain separate work requiring authorization. This configuration
does not establish a live hosted documentation URL.
