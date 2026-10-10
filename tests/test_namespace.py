"""Both import spellings must resolve to the same implementation objects."""

import importlib
import pickle

import pytest

import pnbp
import pretty_notebook


def test_public_exports_and_legacy_note_identity():
    from pnbp.models.note import Note as LegacyNote
    from pretty_notebook.models.note import Note

    assert pnbp.Notebook is pretty_notebook.Notebook
    assert pnbp.Note is pretty_notebook.Note is LegacyNote is Note
    assert pnbp.SettingsError is pretty_notebook.SettingsError
    assert pnbp.IdentityError is pretty_notebook.IdentityError
    assert pickle.loads(pickle.dumps(Note)) is Note


@pytest.mark.parametrize("legacy,canonical", [
    ("models.notebook", "models.notebook"),
    ("models.components.link", "models.components.link"),
    ("helpers.wrappers", "helpers.wrappers"),
    ("settings", "settings"),
    ("cli", "cli"),
    ("commands.collect", "commands.collect"),
    ("_identities", "_internal.identities"),
    ("_publication_plan", "_internal.publication_plan"),
    ("_storage", "_internal.storage"),
])
def test_legacy_module_aliases_share_mutations(monkeypatch, legacy, canonical):
    old = importlib.import_module(f"pnbp.{legacy}")
    new = importlib.import_module(f"pretty_notebook.{canonical}")
    assert old is new
    marker = object()
    monkeypatch.setattr(old, "compatibility_probe", marker, raising=False)
    assert new.compatibility_probe is marker


def test_imports_do_not_initialize_a_notebook(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NOTE_PATH", str(tmp_path))
    importlib.reload(pnbp)
    importlib.reload(pretty_notebook)
    assert list(tmp_path.iterdir()) == []
