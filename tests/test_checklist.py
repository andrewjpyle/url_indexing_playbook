"""Tests for the markdown checklist generator."""

from urllib.parse import quote

from url_indexing_playbook import checklist as checklist_mod
from url_indexing_playbook.targets import IndexingTarget


def test_generate_writes_markdown(tmp_path):
    targets = [
        IndexingTarget(
            slug="a",
            domain="a.example.com",
            urls=["https://a.example.com/x/", "https://a.example.com/y/"],
        ),
        IndexingTarget(slug="b", domain="b.example.com", urls=["https://b.example.com/"]),
    ]
    out = tmp_path / "out.md"
    path = checklist_mod.generate(targets, str(out))
    assert path == str(out)
    contents = out.read_text()
    assert "# GSC Request-Indexing checklist" in contents
    assert "## a.example.com" in contents
    assert "## b.example.com" in contents
    assert "Hosts: 2" in contents
    assert "URLs: 3" in contents


def test_generate_url_encodes_deeplinks(tmp_path):
    targets = [
        IndexingTarget(
            slug="x",
            domain="example.com",
            urls=["https://example.com/path with space/"],
        ),
    ]
    out = tmp_path / "out.md"
    checklist_mod.generate(targets, str(out))
    contents = out.read_text()
    encoded = quote("https://example.com/path with space/", safe="")
    assert encoded in contents


def test_generate_default_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(checklist_mod, "time", __import__("time"))
    targets = [IndexingTarget(slug="x", domain="x.com", urls=["https://x.com/"])]
    path = checklist_mod.generate(targets)
    assert path.startswith("/tmp/gsc-checklist-")
    assert path.endswith(".md")
