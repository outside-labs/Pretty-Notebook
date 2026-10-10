"""Exercise an installed release with fresh or legacy synthetic notebook data."""

import argparse
from importlib.metadata import version
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pnbp
from pretty_notebook import Notebook
from pretty_notebook.settings import initialize_notebook


def exercise(root, expected_version):
    assert version("pretty-notebook") == expected_version
    assert pnbp.Notebook is Notebook
    if not (root / "first.md").exists():
        (root / "first.md").write_text("# Overview\n\nA café idea. #public #work\n", encoding="utf-8")
        (root / "index.md").write_text("# Index\n\n[[first#overview]] #public #work\n", encoding="utf-8")
    legacy = root / "pnbp_settings.json"
    if not legacy.exists():
        legacy.write_text(json.dumps({"NOTE_PATH": str(root), "NOTE_NESTED": "all"}))
    before = {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}
    initialize_notebook(root, migrate=True, dry_run=True)
    assert before == {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}
    initialize_notebook(root, migrate=True)
    assert (root / ".pnbp/legacy-settings.json").read_bytes() == before[legacy.name]
    nb = Notebook.open(root, settings={"NOTE_NESTED": "all", "HTML_PATH": "html", "ROUTE_MODE": "flat"})
    nb.initialize_identities()
    note = nb.get("first", fuzzy=False)
    original_id = note.note_id
    source = (root / "first.md").read_bytes()
    note.md_out = note.current_md + "\nA pending release check.\n"
    assert nb.search("pending release check") and (root / "first.md").read_bytes() == source
    note = note.save(nb)
    assert note.note_id == original_id and not note.is_unsaved
    nb.rename_note("first", "overview")
    assert nb.get("overview", fuzzy=False).note_id == original_id
    assert "[[overview#overview]]" in nb.get("index", fuzzy=False).current_md
    nb.generate_note("guides/deep", "# Deep note\n\n#public #work\n")
    assert "/guides-deep" in {route["route"] for route in nb.publication_routes()["routes"]}
    nb.write_commits_to_local_html()
    hierarchical = Notebook.open(root, settings={"NOTE_NESTED": "all", "HTML_PATH": "html", "ROUTE_MODE": "hierarchical"})
    assert "/guides/deep" in {route["route"] for route in hierarchical.publication_routes()["routes"]}
    assert hierarchical.get("overview", fuzzy=False).note_id == original_id
    assert hierarchical.navigation_index(public_only=True).directory().directories == ("guides",)
    assert hierarchical.search("café", tags=("work",))
    hierarchical.write_commits_to_local_html()
    assert (root / "html/guides/deep.html").is_file()
    print(json.dumps({"version": expected_version, "settings_migration": "passed", "pending_save": "passed",
                      "identity_rename_backlinks": "passed", "flat_to_hierarchical": "passed",
                      "search_navigation": "passed", "local_publication": "passed"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--notebook", type=Path)
    args = parser.parse_args()
    if args.notebook is not None:
        exercise(args.notebook.resolve(), args.version)
    else:
        with TemporaryDirectory(prefix="notebook-release-") as directory:
            exercise(Path(directory), args.version)
