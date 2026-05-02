"""End-to-end tests for the ping_search_engines management command."""

from unittest.mock import patch

import pytest
from django.core.management import call_command


def _fake_gsc(site_url, inspection_url):
    return {
        "verdict": "PASS",
        "coverage_state": "Indexed",
        "last_crawl_time": "2026-04-30T12:00:00Z",
    }


def test_dry_run_no_external_calls(db, capsys, tmp_path):
    call_command(
        "ping_search_engines",
        "--dry-run",
        "--output-checklist", str(tmp_path / "checklist.md"),
    )
    out = capsys.readouterr().out
    assert "[dry-run]" in out
    assert "ping_search_engines" in out
    assert (tmp_path / "checklist.md").is_file()


def test_runs_gsc_and_records_results(db, tmp_path):
    from url_indexing_playbook.models import IndexingRun

    with patch("tests.test_command_ping._fake_gsc", side_effect=_fake_gsc) as gsc:
        call_command(
            "ping_search_engines",
            "--no-indexnow",
            "--gsc-client-callable", "tests.test_command_ping._fake_gsc",
            "--output-checklist", str(tmp_path / "checklist.md"),
            "--sleep", "0",
        )
        assert gsc.call_count == 3  # 2 + 1 URLs across the two test sites

    run = IndexingRun.objects.latest("started_at")
    assert run.command == "ping_search_engines"
    assert run.status == "completed"
    assert run.gsc_attempted == 3
    assert run.gsc_ok == 3
    assert run.gsc_failed == 0
    assert run.indexnow_attempted == 0


def test_gsc_callable_required_when_gsc_enabled(db, tmp_path):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError, match="gsc-client-callable"):
        call_command(
            "ping_search_engines",
            "--no-indexnow",
            "--output-checklist", str(tmp_path / "checklist.md"),
        )


def test_indexnow_key_required_when_indexnow_enabled(db, tmp_path, monkeypatch):
    from django.core.management.base import CommandError

    monkeypatch.delenv("INDEXNOW_KEY", raising=False)
    with pytest.raises(CommandError, match="indexnow-key"):
        call_command(
            "ping_search_engines",
            "--no-gsc",
            "--output-checklist", str(tmp_path / "checklist.md"),
        )


def test_slug_filter(db, tmp_path):
    from url_indexing_playbook.models import IndexingRun

    call_command(
        "ping_search_engines",
        "--dry-run",
        "--slugs", "site_a",
        "--output-checklist", str(tmp_path / "checklist.md"),
    )
    # Dry-run does not create an IndexingRun row (this command does — verify)
    run = IndexingRun.objects.latest("started_at")
    assert run.target_count == 1
    assert run.url_count == 2
