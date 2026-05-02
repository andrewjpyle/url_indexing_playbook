"""Default TargetSource — settings dict OR CSV file.

Use this if you don't have a model yet. If you do, write your own TargetSource
against it and pass `--target-source dotted.path.YourSource`.
"""

import csv
from collections.abc import Iterable
from pathlib import Path

from url_indexing_playbook.targets import IndexingTarget, TargetSource


class DefaultTargetSource(TargetSource):
    """Reads targets from `settings.URL_INDEXING_TARGETS` (dict) or a CSV file.

    Settings dict shape:

        URL_INDEXING_TARGETS = {
            "site_a": {
                "domain": "example.com",
                "urls": ["https://example.com/about/", "https://example.com/blog/"],
                "gsc_site_url": "sc-domain:example.com",  # optional
            },
            ...
        }

    CSV shape (slug,domain,url — one URL per row, multiple rows per slug):

        slug,domain,url
        site_a,example.com,https://example.com/about/
        site_a,example.com,https://example.com/blog/
        site_b,b.example.com,https://b.example.com/

    Construct directly with `csv_path=...` to read from a file instead of settings.
    """

    def __init__(self, csv_path: str | None = None) -> None:
        self.csv_path = csv_path

    def iter_targets(
        self,
        *,
        slugs: list[str] | None = None,
    ) -> Iterable[IndexingTarget]:
        if self.csv_path:
            yield from self._iter_csv(slugs=slugs)
        else:
            yield from self._iter_settings(slugs=slugs)

    def _iter_settings(
        self,
        *,
        slugs: list[str] | None,
    ) -> Iterable[IndexingTarget]:
        from django.conf import settings

        targets_dict = getattr(settings, "URL_INDEXING_TARGETS", {})
        if not targets_dict:
            raise ValueError(
                "No URL_INDEXING_TARGETS in settings and no csv_path passed. "
                "Either set URL_INDEXING_TARGETS in settings.py, or write a "
                "custom TargetSource."
            )

        slug_filter = set(slugs) if slugs else None
        for slug in sorted(targets_dict):
            if slug_filter and slug not in slug_filter:
                continue
            entry = targets_dict[slug]
            yield IndexingTarget(
                slug=slug,
                domain=entry["domain"],
                urls=list(entry["urls"]),
                gsc_site_url=entry.get("gsc_site_url", ""),
            )

    def _iter_csv(
        self,
        *,
        slugs: list[str] | None,
    ) -> Iterable[IndexingTarget]:
        path = Path(self.csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")

        # Group by slug
        slug_filter = set(slugs) if slugs else None
        groups: dict[str, dict] = {}
        with path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                slug = row["slug"].strip()
                if slug_filter and slug not in slug_filter:
                    continue
                if slug not in groups:
                    groups[slug] = {
                        "domain": row["domain"].strip(),
                        "urls": [],
                    }
                groups[slug]["urls"].append(row["url"].strip())

        for slug in sorted(groups):
            yield IndexingTarget(
                slug=slug,
                domain=groups[slug]["domain"],
                urls=groups[slug]["urls"],
            )
