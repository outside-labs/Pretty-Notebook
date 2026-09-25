from pnbp import Notebook
from pnbp.commands.correct import _delete_all_empty, _delete_all_pnbp
from pnbp.commands.graph import _delete_all_graph_dash_name


def make_notebook(monkeypatch, tmp_path, files):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	for name, text in files.items():
		path = tmp_path / f"{name}.md"
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(text, encoding="utf-8")
	return Notebook()


def test_delete_all_empty_rechecks_stale_report(monkeypatch, tmp_path):
	nb = make_notebook(
		monkeypatch,
		tmp_path,
		{
			"all empty": "[[alpha]]\n",
			"alpha": "This note is no longer empty.\n",
		},
	)

	_delete_all_empty(nb=nb)

	assert (tmp_path / "alpha.md").exists()
	assert "alpha" in nb.notes


def test_delete_all_empty_refuses_unsaved_changes(monkeypatch, tmp_path):
	nb = make_notebook(
		monkeypatch,
		tmp_path,
		{
			"all empty": "[[alpha]]\n",
			"alpha": "",
		},
	)
	nb.notes["alpha"].md_out = "pending content\n"

	try:
		_delete_all_empty(nb=nb)
	except RuntimeError as error:
		assert "unsaved" in str(error)
	else:
		raise AssertionError("cleanup accepted unsaved note changes")

	assert (tmp_path / "alpha.md").exists()
	assert nb.notes["alpha"].md_out == "pending content\n"


def test_delete_all_empty_removes_only_currently_empty_target_from_memory(monkeypatch, tmp_path):
	nb = make_notebook(
		monkeypatch,
		tmp_path,
		{
			"all empty": "[[alpha]]\n[[beta]]\n",
			"alpha": "",
			"beta": "kept\n",
		},
	)

	_delete_all_empty(nb=nb)

	assert not (tmp_path / "alpha.md").exists()
	assert "alpha" not in nb.notes
	assert (tmp_path / "beta.md").exists()
	assert "beta" in nb.notes


def test_delete_all_pnbp_updates_notebook_state(monkeypatch, tmp_path):
	nb = make_notebook(
		monkeypatch,
		tmp_path,
		{
			"generated": "#pnbp\n",
			"ordinary": "hello\n",
		},
	)

	_delete_all_pnbp(nb=nb)

	assert not (tmp_path / "generated.md").exists()
	assert "generated" not in nb.notes
	assert "ordinary" in nb.notes


def test_delete_graphs_requires_prefix_and_mermaid_and_updates_state(monkeypatch, tmp_path):
	nb = make_notebook(
		monkeypatch,
		tmp_path,
		{
			"graph-real": "```mermaid\ngraph LR\nA --> B\n```\n",
			"graph-text": "not a generated graph\n",
			"ordinary": "```mermaid\ngraph LR\nA --> B\n```\n",
		},
	)

	_delete_all_graph_dash_name(nb=nb)

	assert not (tmp_path / "graph-real.md").exists()
	assert "graph-real" not in nb.notes
	assert (tmp_path / "graph-text.md").exists()
	assert "graph-text" in nb.notes
	assert (tmp_path / "ordinary.md").exists()
	assert "ordinary" in nb.notes
