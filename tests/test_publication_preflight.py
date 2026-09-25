from pathlib import Path

import pytest

from pnbp import Notebook
from pnbp.models.components import Link


class FakeResponse:
	def __init__(self, payload=None):
		self.payload = [] if payload is None else payload

	def json(self):
		return self.payload

	def raise_for_status(self):
		return None

	def __str__(self):
		return "<FakeResponse [201]>"


@pytest.fixture
def publication_root(monkeypatch, tmp_path):
	note_path = tmp_path / "notes"
	image_path = tmp_path / "images"
	html_path = tmp_path / "html"
	for path in (note_path, image_path, html_path):
		path.mkdir()

	monkeypatch.setenv("NOTE_PATH", str(note_path))
	monkeypatch.setenv("IMG_PATH", str(image_path))
	monkeypatch.setenv("HTML_PATH", str(html_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	return note_path, image_path, html_path


def test_slug_policy_keeps_zero_and_separates_nested_names() -> None:
	assert Link("Note10").slugname == "note10"
	assert Link("a/b").slugname == "a-b"


def test_local_publication_rejects_empty_slug_before_writing(
	publication_root,
) -> None:
	note_path, _, html_path = publication_root
	(note_path / "研究.md").write_text("#public\n", encoding="utf-8")
	notebook = Notebook()

	with pytest.raises(ValueError, match="empty publication slug"):
		notebook.write_commits_to_local_html()

	assert list(html_path.iterdir()) == []


def test_remote_publication_rejects_duplicate_slug_before_request(
	publication_root,
	monkeypatch,
) -> None:
	note_path, _, _ = publication_root
	(note_path / "A B.md").write_text("#public\n", encoding="utf-8")
	(note_path / "A-B.md").write_text("#public\n", encoding="utf-8")
	notebook = Notebook()

	def unexpected_request(*args, **kwargs):
		raise AssertionError("publication preflight must run before HTTP requests")

	monkeypatch.setattr("pnbp.models.notebook.requests.get", unexpected_request)

	with pytest.raises(ValueError, match="duplicate publication slug"):
		notebook.post_commits_to_web_api(stage_only=True)


@pytest.mark.parametrize("reference_kind", ["parent", "absolute", "symlink"])
def test_remote_publication_rejects_escaping_image_before_request(
	publication_root,
	monkeypatch,
	reference_kind,
) -> None:
	note_path, image_path, _ = publication_root
	outside = image_path.parent / "private.png"
	outside.write_bytes(b"private")

	if reference_kind == "parent":
		reference = "../private.png"
	elif reference_kind == "absolute":
		reference = str(outside)
	else:
		link = image_path / "escape.png"
		try:
			link.symlink_to(outside)
		except OSError as error:
			pytest.skip(f"symlinks unavailable: {error}")
		reference = link.name

	(note_path / "public.md").write_text(
		f"#public\n![[{reference}]]\n",
		encoding="utf-8",
	)
	notebook = Notebook()

	def unexpected_request(*args, **kwargs):
		raise AssertionError("image preflight must run before HTTP requests")

	monkeypatch.setattr("pnbp.models.notebook.requests.get", unexpected_request)

	with pytest.raises(ValueError, match="image path"):
		notebook.post_commits_to_web_api(stage_only=True)


def test_image_upload_uses_explicit_multipart_metadata_and_closes_file(
	publication_root,
	monkeypatch,
) -> None:
	note_path, image_path, _ = publication_root
	(note_path / "public.md").write_text(
		"#public\n![[photo.png]]\n",
		encoding="utf-8",
	)
	(image_path / "photo.png").write_bytes(b"png")
	notebook = Notebook()
	uploaded_files = []

	monkeypatch.setattr(
		"pnbp.models.notebook.requests.get",
		lambda *args, **kwargs: FakeResponse(),
	)

	def record_post(*args, **kwargs):
		if files := kwargs.get("files"):
			assert set(files) == {"file"}
			filename, file_object, content_type = files["file"]
			assert filename == "photo.png"
			assert content_type == "image/png"
			assert not file_object.closed
			uploaded_files.append(file_object)
		return FakeResponse()

	monkeypatch.setattr("pnbp.models.notebook.requests.post", record_post)

	notebook.post_commits_to_web_api()

	assert len(uploaded_files) == 1
	assert uploaded_files[0].closed
