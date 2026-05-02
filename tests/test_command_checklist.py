"""End-to-end tests for the generate_gsc_checklist management command."""

import pytest
from django.core.management import call_command


def test_writes_to_explicit_path(tmp_path, capsys):
    out = tmp_path / "checklist.md"
    call_command("generate_gsc_checklist", "--output", str(out))
    assert out.is_file()
    contents = out.read_text()
    assert "# GSC Request-Indexing checklist" in contents
    assert "Hosts: 2" in contents


def test_slug_filter(tmp_path, capsys):
    out = tmp_path / "checklist.md"
    call_command("generate_gsc_checklist", "--output", str(out), "--slugs", "site_a")
    contents = out.read_text()
    assert "Hosts: 1" in contents
    assert "a.example.com" in contents
    assert "b.example.com" not in contents


def test_no_targets_raises(tmp_path, settings):

    settings.URL_INDEXING_TARGETS = {}
    with pytest.raises(Exception):  # noqa: B017
        call_command("generate_gsc_checklist", "--output", str(tmp_path / "x.md"))
