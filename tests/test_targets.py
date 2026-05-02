"""Tests for IndexingTarget + DefaultTargetSource."""

import csv

import pytest

from url_indexing_playbook.adapters import DefaultTargetSource
from url_indexing_playbook.targets import IndexingTarget


def test_indexingtarget_default_gsc_site_url():
    t = IndexingTarget(slug="x", domain="example.com", urls=["https://example.com/"])
    assert t.effective_gsc_site_url == "sc-domain:example.com"


def test_indexingtarget_explicit_gsc_site_url():
    t = IndexingTarget(
        slug="x",
        domain="example.com",
        urls=["https://example.com/"],
        gsc_site_url="https://example.com/",
    )
    assert t.effective_gsc_site_url == "https://example.com/"


def test_default_source_reads_settings():
    src = DefaultTargetSource()
    targets = list(src.iter_targets())
    assert len(targets) == 2
    slugs = {t.slug for t in targets}
    assert slugs == {"site_a", "site_b"}


def test_default_source_filters_by_slug():
    src = DefaultTargetSource()
    targets = list(src.iter_targets(slugs=["site_a"]))
    assert len(targets) == 1
    assert targets[0].slug == "site_a"
    assert len(targets[0].urls) == 2


def test_default_source_csv(tmp_path):
    csv_path = tmp_path / "targets.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["slug", "domain", "url"])
        writer.writeheader()
        writer.writerow({"slug": "x", "domain": "x.com", "url": "https://x.com/a/"})
        writer.writerow({"slug": "x", "domain": "x.com", "url": "https://x.com/b/"})
        writer.writerow({"slug": "y", "domain": "y.com", "url": "https://y.com/"})

    src = DefaultTargetSource(csv_path=str(csv_path))
    targets = list(src.iter_targets())
    assert len(targets) == 2
    by_slug = {t.slug: t for t in targets}
    assert len(by_slug["x"].urls) == 2
    assert by_slug["y"].urls == ["https://y.com/"]


def test_default_source_csv_missing(tmp_path):
    src = DefaultTargetSource(csv_path=str(tmp_path / "nope.csv"))
    with pytest.raises(FileNotFoundError):
        list(src.iter_targets())
