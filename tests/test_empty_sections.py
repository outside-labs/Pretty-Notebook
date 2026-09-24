from pnbp.models import Note


def empty_note():
	return Note(
		name="empty",
		md="",
		links=[],
		tags=[],
		urls=[],
		codeblocks=[],
		mtime="",
	)


def test_empty_note_alias_and_footnote_checks_are_safe():
	note = empty_note()

	assert note.aliases is None
	assert note.footnotes is None


def test_empty_note_can_prepend_first_section():
	note = empty_note()

	note.prepend_section("first")

	assert note.md_out == "first"


def test_empty_note_can_append_first_section():
	note = empty_note()

	note.append_section("first")

	assert note.md_out == "first"


def test_empty_note_can_insert_first_section():
	note = empty_note()

	note.insert_section(0, "first")

	assert note.md_out == "first"
