"""Check emitted documentation links and reserved Sphinx page collisions."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

RESERVED_PAGES = {"search", "genindex", "py-modindex"}


class Page(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.ids = set()
        self.links = []
        self.heading = []
        self.in_heading = False
        self.feed(content)

    def handle_starttag(self, tag, attributes):
        if tag == "h1" and not self.heading:
            self.in_heading = True
        values = dict(attributes)
        if "id" in values:
            self.ids.add(values["id"])
        if tag == "a" and "name" in values:
            self.ids.add(values["name"])
        if "href" in values:
            self.links.append(values["href"])

    def handle_data(self, content):
        if self.in_heading:
            self.heading.append(content)

    def handle_endtag(self, tag):
        if tag == "h1":
            self.in_heading = False


def check_output(output, *, sources=None):
    """Return actionable errors for local output paths and fragment targets."""
    output = Path(output).resolve()
    errors = []
    if sources is not None:
        for source in sorted(Path(sources).iterdir()):
            if source.suffix in {".md", ".rst"} and source.stem.casefold() in RESERVED_PAGES:
                errors.append(f"{source.name}: source name collides with a generated Sphinx page")
    pages = {path.resolve(): Page(path.read_text(encoding="utf-8")) for path in output.rglob("*.html")}
    if not pages:
        errors.append("No generated HTML pages found")
    for path, page in sorted(pages.items()):
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not link:
                continue
            target = (output / unquote(url.path).lstrip("/") if url.path.startswith("/")
                      else path.parent / unquote(url.path) if url.path else path).resolve()
            if target.is_dir():
                target /= "index.html"
            if not target.is_relative_to(output) or not target.is_file():
                errors.append(f"{path.relative_to(output)}: missing local target {link}")
            elif url.fragment and target.suffix == ".html" and unquote(url.fragment) not in pages[target].ids:
                errors.append(f"{path.relative_to(output)}: missing local anchor {link}")
    # Verify the notebook-search guide survived alongside Sphinx's own search.
    if sources is not None and (Path(sources) / "local-search.md").exists():
        guide = pages.get(output / "local-search.html")
        search = pages.get(output / "search.html")
        if guide is None or "local-notebook-search" not in guide.ids:
            errors.append("local-search.html: missing notebook-search guide")
        if search is None or "".join(search.heading).strip("¶ \n") != "Search":
            errors.append("search.html: missing generated documentation search")
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sources", type=Path)
    arguments = parser.parse_args()
    errors = check_output(arguments.output, sources=arguments.sources)
    if errors:
        for error in errors[:20]:
            print(error)
        if len(errors) > 20:
            print(f"{len(errors) - 20} additional documentation link errors")
        return 1
    print("Generated documentation links and pages are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
