"""Compare what each host's sitemap offers against the URLs you plan to submit.

Read-only: it fetches robots.txt and sitemaps, never submits anything.

Usage:
    manage.py sitemap_funnel
    manage.py sitemap_funnel --slugs site_a,site_b --json
"""

import json

import requests
from django.core.management.base import BaseCommand, CommandError

from url_indexing_playbook.management.commands._common import (
    DEFAULT_TARGET_SOURCE,
    load_target_source,
    parse_slugs,
)
from url_indexing_playbook.sitemaps import count_sitemap_urls, resolve_sitemap_url


class Command(BaseCommand):
    help = "Report sitemap URL counts per host next to the URLs queued for submission."

    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--target-source", default=DEFAULT_TARGET_SOURCE)
        parser.add_argument("--slugs", default="", help="Comma-separated slug filter.")
        parser.add_argument("--json", dest="emit_json", action="store_true")

    def handle(self, *args, **options):
        source = load_target_source(options["target_source"])
        targets = list(source.iter_targets(slugs=parse_slugs(options["slugs"])))
        if not targets:
            raise CommandError("No targets matched the selected filters.")

        rows = []
        for t in targets:
            row = {"slug": t.slug, "domain": t.domain, "queued_urls": len(t.urls)}
            try:
                row["sitemap_url"] = resolve_sitemap_url(t.domain)
                row["sitemap_urls"] = count_sitemap_urls(t.domain)
            except (requests.RequestException, ValueError) as e:
                row["sitemap_urls"] = None
                row["error"] = str(e)
            rows.append(row)

        if options["emit_json"]:
            self.stdout.write(json.dumps(rows, indent=2))
            return
        for r in rows:
            shown = "ERROR" if r["sitemap_urls"] is None else r["sitemap_urls"]
            self.stdout.write(
                f"{r['domain']:36s} sitemap={shown}  queued={r['queued_urls']}"
            )
            if "error" in r:
                self.stdout.write(self.style.ERROR(f"    {r['error']}"))
