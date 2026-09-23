import pytest

from pnbp import Notebook
from pnbp.models.components import CodeBlock, Link, Tag, Url


def test_component_instances_have_stable_types_and_string_equality():
	tag = Tag("#topic")

	assert isinstance(tag, Tag)
	assert tag == "#topic"
	unequal = tag != "#topic"
	assert unequal is False
	assert hash(tag) == hash("#topic")
	assert "#topic" in {tag}
	assert tag.tag == "#topic"
	assert repr(tag) == "Tag('#topic')"


def test_component_keyword_constructors_match_documented_fields():
	assert Tag(tag="#topic") == Tag("#topic")
	assert Link(link="Topic") == Link("Topic")
	assert Url(url="https://example.com") == Url("https://example.com")
	assert CodeBlock(codeblock="python\npass\n") == CodeBlock("python\npass\n")


def test_explicit_matching_is_separate_from_equality():
	tag = Tag("#topic")
	link = Link("Topic#Section")

	assert tag != "topic"
	assert tag.matches("topic")
	assert tag.matches("#topic")
	assert link.matches("topic")
	assert link.matches("[[Topic#Other]]")
	assert not link.matches("other")


@pytest.fixture
def note(monkeypatch, tmp_path):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	(tmp_path / "alpha.md").write_text(
		"#first #second\n[[Target#Section]] and [[Other|Label]]\n",
		encoding="utf-8",
	)
	return Notebook().notes["alpha"]


def test_tag_queries_use_explicit_any_and_all_semantics(note):
	assert note.is_tagged(tags=["missing", "second"])
	assert not note.is_tagged(tags=["missing", "second"], to_all=True)
	assert note.is_tagged(tags=["first", "#second"], to_all=True)
	assert note.is_tagged(at_all=True)


def test_link_queries_use_explicit_any_and_all_semantics(note):
	assert note.is_linked(links=["missing", "target"])
	assert not note.is_linked(links=["missing", "target"], to_all=True)
	assert note.is_linked(links=["target", "other"], to_all=True)
	assert note.is_linked("[[Target#Different]]")
	assert note.is_linked(at_all=True)
