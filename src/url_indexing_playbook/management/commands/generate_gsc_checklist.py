"""Generate the GSC manual 'Request Indexing' deeplink checklist.

No external API calls. Pure markdown.

Usage:
    manage.py generate_gsc_checklist
    manage.py generate_gsc_checklist --output ./checklist.md
    manage.py generate_gsc_checklist --slugs site_a,site_b
"""

from django.core.management.base import BaseCommand, CommandError

from url_indexing_playbook import checklist as checklist_mod
from url_indexing_playbook.management.commands._common import (
    DEFAULT_TARGET_SOURCE,
    load_target_source,
    parse_slugs,
)


class Command(BaseCommand):
    help = "Generate a markdown checklist of GSC 'Request Indexing' deeplinks."

    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--target-source", default=DEFAULT_TARGET_SOURCE)
        parser.add_argument("--slugs", default="")
        parser.add_argument(
            "--output",
            default="",
            help="Output path (default: /tmp/gsc-checklist-<timestamp>.md)",
        )

    def handle(self, *args, **options):
        target_source = load_target_source(options["target_source"])
        slug_filter = parse_slugs(options["slugs"])

        targets = list(target_source.iter_targets(slugs=slug_filter))
        if not targets:
            raise CommandError("No targets matched the selected filters.")

        path = checklist_mod.generate(targets, options["output"] or None)
        url_count = sum(len(t.urls) for t in targets)
        self.stdout.write(self.style.SUCCESS(
            f"Wrote checklist for {len(targets)} hosts ({url_count} URLs)\n"
            f"  → {path}"
        ))
