from dataclasses import replace

import pytest

from pretty_notebook import Notebook
from pretty_notebook._internal import identities as _identities
from pretty_notebook._internal.links import GraphIndex, wiki_targets
from pretty_notebook.models.components import Link


@pytest.fixture
def graph():
	return GraphIndex({
		"root.md": "# Heading One\n\nOther\n-----\n\n# Explicit {: #custom }\n",
		"left/same.md": "Left",
		"right/same.md": "Right",
		"left/source.md": "[[./same#Missing|Label]] [[same]] [[root#Heading One]] [[absent]]",
	})


def test_root_relative_and_ambiguous_basename_resolution(graph):
	assert graph.resolve("root", source="left/source.md").path == "root.md"
	assert graph.resolve("./same", source="left/source.md").path == "left/same.md"
	assert graph.resolve("../right/same.MD", source="left/source.md").path == "right/same.md"
	assert graph.resolve("/left/same").path == "left/same.md"
	assert graph.resolve("same").state == "ambiguous"
	assert graph.resolve("same").candidates == ("left/same.md", "right/same.md")
	assert graph.resolve("./same").state == "invalid"
	assert graph.resolve("../../outside", source="left/source.md").state == "invalid"
	assert graph.resolve("absent").state == "missing"


def test_root_path_precedes_basename_or_alias_fallback():
	graph = GraphIndex({"same.md": "Root", "left/same.md": "Nested"})
	assert graph.resolve("same").path == "same.md"
	assert graph.resolve("left/same").path == "left/same.md"


def test_case_collisions_are_ambiguous_even_for_exact_spelling():
	graph = GraphIndex({"Entry.md": "A", "entry.md": "B"})
	assert graph.resolve("Entry").state == "ambiguous"


def test_fragment_diagnostics_support_standard_heading_ids(graph):
	assert graph.resolve("root#Heading One").heading_state == "valid"
	assert graph.resolve("root#heading-one|Label").heading_state == "valid"
	assert graph.resolve("root#other").heading_state == "valid"
	assert graph.resolve("root#custom").heading_state == "valid"
	assert graph.resolve("root#unknown").heading_state == "missing"
	assert graph.resolve("#Missing", source="left/same.md").heading_state == "missing"
	assert graph.resolve("#Heading One", source="root.md").path == "root.md"
	assert {item["state"] for item in graph.diagnostics()} == {"resolved", "missing", "ambiguous"}
	assert len(graph.backlinks("root.md")) == 1


def test_custom_heading_syntax_is_reported_as_unknown():
	graph = GraphIndex({"note.md": "# [[Target|Label]]\n<h2 id='raw'>Raw</h2>"})
	assert graph.resolve("note#unproven").heading_state == "unknown"


@pytest.mark.parametrize("literal", [
	"`[[target]]`", "``[[target]] ` inner``", "```text\n[[target]]\n```",
	"~~~~text\n[[target]]\n~~~~~", "```text\n[[target]]", "    [[target]]\n",
	"\t[[target]]", "<pre>[[target]]</pre>", "<code>[[target]]</code>",
	"<!-- [[target]] -->", "<div class='mermaid'>[[target]]</div>",
	"![[target.png]]", "\\[[target]]",
])
def test_literal_spans_and_embedded_images_are_opaque(literal):
	source = f"[[before]]\n{literal}\n[[after]]"
	targets = list(wiki_targets(source))
	expected = ["before"] if literal == "```text\n[[target]]" else ["before", "after"]
	assert [target.target for target in targets] == expected


def test_exact_spans_preserve_whitespace_fragment_label_and_line_endings():
	text = "Prose\r\n[[  target # Heading | Label | with pipe ]] elsewhere target.\r\n"
	target, = wiki_targets(text)
	assert target.target == "target"
	assert target.fragment == "Heading"
	assert target.label == " Label | with pipe "
	assert target.line == 2
	updated = text[:target.target_start] + "new/path" + text[target.target_end:]
	assert updated == "Prose\r\n[[  new/path # Heading | Label | with pipe ]] elsewhere target.\r\n"


def test_metadata_titles_aliases_ids_and_alias_collisions(tmp_path, monkeypatch):
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	(tmp_path / "one.md").write_text("# Header")
	(tmp_path / "two.md").write_text("Other")
	_identities.initialize_identities(tmp_path)
	index = _identities.load_index(tmp_path)
	one, two = index.notes
	index = replace(index, notes=(replace(one, title="Title", aliases=("Alias", "Shared")), replace(two, aliases=("Shared",))))
	with _identities.identity_operation(tmp_path) as expected:
		_identities._write_index(tmp_path, index, expected)
	nb = Notebook(tmp_path)
	assert nb.resolve_link("Title").note_id == one.id
	assert nb.resolve_link("Alias").path == "one.md"
	assert nb.resolve_link(f"id:{two.id}").path == "two.md"
	assert nb.resolve_link("Shared").state == "ambiguous"
	assert Link("Alias#Header|Shown").resolve(nb) is nb.notes["one"]
	assert Link("Shared").resolve(nb) is None


def test_graph_covers_nested_notes_and_pending_text_without_writes(tmp_path, monkeypatch):
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	(tmp_path / "one.md").write_text("[[missing]]")
	(tmp_path / "nested").mkdir()
	(tmp_path / "nested" / "two.md").write_text("Two")
	nb = Notebook(tmp_path)
	assert len(nb.notes) == 1
	nb.notes["one"].md_out = "[[nested/two]]"
	graph = nb.graph_index()
	assert len(graph.backlinks("nested/two.md")) == 1
	assert not graph.diagnostics()
	assert Link("nested/two").resolve(nb).source_path == "nested/two.md"
	assert (tmp_path / "one.md").read_text() == "[[missing]]"
	assert not (tmp_path / ".pnbp").exists()
