# API and CLI reference

This reference documents the current checkout's selected public entry points.
Tutorials explain the workflows in [settings](settings.md),
[editing](editing.md), [links](links.md), [identities](identities.md), and
[checked publishing](checked-publishing.md). API signatures and command help
below are generated from the package itself when the documentation is built.

## Notebook

Import the notebook with `from pretty_notebook import Notebook`. Opening an existing path
does not initialize settings or identity metadata. The `open` entry point can
also be used as `Notebook.open(path)`; `nb.open()` reloads an existing instance.

```{eval-rst}
.. autoclass:: pretty_notebook.Notebook
   :members: get, reload, generate_note, get_tagged, search, navigation_index, traversal, resolve_link, graph_index, rename_note, move_note, initialize_identities, identity_status, publication_routes, prepare_publication, execute_publication, post_favicon
```

## Note

Get notes from a notebook; for type imports use `from pretty_notebook import Note`.
Loaded Markdown and pending Markdown are distinct. Saving checks the source
file for concurrent changes and returns the refreshed note.

```{eval-rst}
.. autoclass:: pretty_notebook.Note
   :members: current_md, md_out, is_unsaved, discard_changes, save
```

## Settings

```{eval-rst}
.. autoclass:: pretty_notebook.NotebookSettings
```

```{eval-rst}
.. autoexception:: pretty_notebook.SettingsError
```

## Search and navigation

```{eval-rst}
.. autoclass:: pretty_notebook.SearchHit

.. autoclass:: pretty_notebook.NavigationIndex
   :members: directory, entry, breadcrumbs, outline, backlinks, neighbors, related

.. autoclass:: pretty_notebook.NavigationHistory
   :members: visit, current, back, forward
```

## CLI overview

Select a notebook before the command with `--notebook PATH` or `--profile NAME`.
Command help reads the command registry without opening or modifying a notebook.

```{pnbp-cli-help}
```

## Editing commands

```{pnbp-cli-help} note
```

```{pnbp-cli-help} note edit
```

## Publication and favicon

```{pnbp-cli-help} commit-remote
```

```{pnbp-cli-help} commit-settings
```

```{pnbp-cli-help} favicon
```

### VPS deployment

See [VPS setup and upgrades](vps-deployment.md). Commands generate inspectable
bundles and read-only diagnostics without opening a notebook.

```{pnbp-cli-help} deploy
```

```{pnbp-cli-help} deploy upgrade
```
