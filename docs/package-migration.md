# Package naming in 0.10 development

The canonical distribution is prepared as `pretty-notebook`, with the import
package `pretty_notebook`. The executable remains `pnbp`:

```python
from pretty_notebook import Notebook, Note
```

The development version is `0.10.0.dev0`. Install the checkout with
`python -m pip install --editable .`; this page does not announce a published
0.10 package. The released `pnbp==0.9.0` remains a separate historical release.

The new distribution includes compatibility wrappers for `pnbp`, its models,
helpers, commands, CLI and former private modules. Existing imports resolve to
the same classes, exceptions and leaf modules, so a notebook is not maintained
twice. Prefer the canonical import in new code. No import initializes notebook
settings, identities, Git or server state.

Private implementation helpers now live in `pretty_notebook._internal`, with
ordinary descriptive module names. The underscore marks a private package;
applications should use the documented public API. The compatibility package
retains old private module spellings for the transition.

Distribution names and import names are independent. PyPI will not redirect
`pip install pnbp` to the new distribution. Before publishing, confirm ownership
of the new PyPI name and configure its trusted publisher. A later transitional
`pnbp` distribution should depend on `pretty-notebook` and contain no competing
implementation modules. Upgrade environments by uninstalling the old `pnbp`
distribution before installing the new one; installing both old wheels can
overwrite their shared compatibility paths. Publishing either distribution is
a separate release operation.

`uv.lock` is committed for reproducible development installations. It pins
development resolution without constraining downstream library users beyond
`pyproject.toml`. Update the lock when metadata or dependencies change; use
`uv lock --check` to detect drift. The web app retains its separate hashed
`apps/web/requirements.lock`.
