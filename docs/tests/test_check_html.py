"""Detect actual emitted-link and generated-page regressions."""

import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

spec = importlib.util.spec_from_file_location("check_html", Path(__file__).resolve().parents[1] / "check_html.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class OutputLinks(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_relative_files_encoded_anchors_and_external_links(self):
        (self.root / "index.html").write_text('<a href="topic.html#caf%C3%A9">Topic</a><a href="https://example.com/missing">External</a><a href="#self">Self</a><b id="self"></b>')
        (self.root / "topic.html").write_text('<b id="café"></b><a href="./">Home</a>')
        self.assertEqual(checker.check_output(self.root), [])

    def test_missing_file_and_anchor_fail(self):
        (self.root / "index.html").write_text('<a href="missing.html">Missing</a><a href="topic.html#missing">Anchor</a>')
        (self.root / "topic.html").write_text('<b id="present"></b>')
        errors = checker.check_output(self.root)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("missing local target" in error for error in errors))
        self.assertTrue(any("missing local anchor" in error for error in errors))

    def test_reserved_source_name_is_rejected(self):
        sources = self.root / "sources"
        sources.mkdir()
        (sources / "search.md").write_text('# Local notebook search')
        (self.root / "index.html").write_text('<h1>Index</h1>')
        self.assertTrue(any("collides" in error for error in checker.check_output(self.root, sources=sources)))

    def test_overwritten_search_guide_is_detected(self):
        sources = self.root / "sources"
        sources.mkdir()
        (sources / "local-search.md").write_text('# Local notebook search')
        (self.root / "index.html").write_text('<h1>Index</h1>')
        (self.root / "local-search.html").write_text('<h1>Search</h1>')
        (self.root / "search.html").write_text('<h1>Local notebook search</h1>')
        self.assertEqual(len(checker.check_output(self.root, sources=sources)), 2)

    def test_empty_output_fails(self):
        self.assertEqual(checker.check_output(self.root), ["No generated HTML pages found"])

    def test_correct_search_pages_coexist_with_sidebar_links(self):
        sources = self.root / "sources"
        sources.mkdir()
        (sources / "local-search.md").write_text('# Local notebook search')
        (self.root / "local-search.html").write_text('<h1 id="local-notebook-search">Local notebook search</h1><a href="search.html">Search docs</a>')
        (self.root / "search.html").write_text('<h1>Search</h1><a href="local-search.html">Local notebook search</a>')
        self.assertEqual(checker.check_output(self.root, sources=sources), [])
