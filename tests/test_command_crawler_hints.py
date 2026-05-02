"""End-to-end tests for the enable_crawler_hints management command."""

from unittest.mock import patch

import pytest
from django.core.management import call_command


def test_dry_run(db, capsys):
    call_command("enable_crawler_hints", "--dry-run")
    out = capsys.readouterr().out
    assert "[dry-run]" in out
    assert "enable_crawler_hints" in out


def test_skip_both_raises(db):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError, match="leave nothing to do"):
        call_command("enable_crawler_hints", "--skip-enable", "--skip-purge", "--dry-run")


def test_runs_enable_and_purge(db, monkeypatch):
    from url_indexing_playbook.models import IndexingRun

    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")

    with patch(
        "url_indexing_playbook.cloudflare.resolve_zone_id",
        return_value="zone-abc",
    ), patch(
        "url_indexing_playbook.cloudflare.enable_crawler_hints",
        return_value={"ok": True, "value": True, "status": "ok"},
    ), patch(
        "url_indexing_playbook.cloudflare.purge_cache",
        return_value={"ok": True, "status_code": 200, "url_count": 1},
    ):
        call_command("enable_crawler_hints", "--sleep", "0")

    run = IndexingRun.objects.latest("started_at")
    assert run.command == "enable_crawler_hints"
    assert run.status == "completed"
    assert run.cloudflare_enable_attempted == 2
    assert run.cloudflare_enable_ok == 2
    assert run.cloudflare_purge_attempted == 2
    assert run.cloudflare_purge_ok == 2


def test_skip_enable(db, monkeypatch):
    from url_indexing_playbook.models import IndexingRun

    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")

    with patch(
        "url_indexing_playbook.cloudflare.resolve_zone_id",
        return_value="zone-abc",
    ), patch(
        "url_indexing_playbook.cloudflare.purge_cache",
        return_value={"ok": True, "status_code": 200, "url_count": 1},
    ) as purge:
        call_command("enable_crawler_hints", "--skip-enable", "--sleep", "0")

    run = IndexingRun.objects.latest("started_at")
    assert run.cloudflare_enable_attempted == 0
    assert run.cloudflare_purge_attempted == 2
    assert purge.call_count == 2
