"""Check the site before it is served: every local link and image resolves,
every #fragment names an id on its page, and every image has alt text.

    python3 .github/check_site.py        # from the repository root

External links are not fetched. Standard library only.
"""
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
SKIP = ("http:", "https:", "mailto:", "tel:", "data:", "javascript:")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.no_alt = [], set(), []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        for key in ("href", "src"):
            if a.get(key):
                self.refs.append((self.getpos()[0], a[key]))
        if tag == "img" and a.get("alt") is None:
            self.no_alt.append((self.getpos()[0], a.get("src", "?")))


def parse(path, cache={}):
    if path not in cache:
        page = Page()
        page.feed(path.read_text(encoding="utf8"))
        cache[path] = page
    return cache[path]


def main():
    problems = []
    pages = sorted(p for p in ROOT.rglob("*.html") if ".git" not in p.parts)
    for path in pages:
        page, rel = parse(path), path.relative_to(ROOT)
        for line, src in page.no_alt:
            problems.append(f"{rel}:{line}: image {src} has no alt text")
        for line, ref in page.refs:
            if ref.startswith(SKIP):
                continue
            parts = urlsplit(ref)
            target = path if not parts.path else (
                ROOT / parts.path.lstrip("/") if parts.path.startswith("/") else path.parent / unquote(parts.path))
            if target.is_dir():
                target = target / "index.html"
            if not target.resolve().is_relative_to(ROOT):
                problems.append(f"{rel}:{line}: {ref} points outside the site")
            elif not target.exists():
                problems.append(f"{rel}:{line}: {ref} does not exist")
            elif parts.fragment and target.suffix == ".html" and unquote(parts.fragment) not in parse(target.resolve()).ids:
                problems.append(f"{rel}:{line}: {ref} names no id on that page")
    print("\n".join(problems) or f"ok: {len(pages)} pages")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
