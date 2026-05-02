"""Cloudflare Crawler Hints + bulk cache purge.

Strictly better IndexNow path for Cloudflare-fronted sites — uses CF's own
key, no origin key file required.

Two operations per host:
  1. POST /zones/{id}/flags/products/cache/changes  (enable Crawler Hints)
  2. POST /zones/{id}/purge_cache                    (trigger the IndexNow ping)

The purge is what triggers Crawler Hints to ping IndexNow — without a
content-fingerprint change, Cloudflare has no event to fire on.

Usage:
    manage.py enable_crawler_hints --dry-run
    manage.py enable_crawler_hints --slugs site_a,site_b
    manage.py enable_crawler_hints --skip-purge
    manage.py enable_crawler_hints --skip-enable

Auth: reads CLOUDFLARE_API_TOKEN (Bearer, modern, preferred), falling back
to CLOUDFLARE_API_KEY + CLOUDFLARE_EMAIL (Global Key, legacy).
"""

import json
import time

from django.core.management.base import BaseCommand, CommandError

from url_indexing_playbook import cloudflare as cf
from url_indexing_playbook.management.commands._common import (
    DEFAULT_TARGET_SOURCE,
    load_callable,
    load_target_source,
    parse_slugs,
)


class Command(BaseCommand):
    help = "Enable Cloudflare Crawler Hints and bulk-purge URLs across a target list."

    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--target-source", default=DEFAULT_TARGET_SOURCE)
        parser.add_argument("--slugs", default="")
        parser.add_argument("--skip-enable", action="store_true",
                            help="Skip the Crawler Hints toggle; only purge.")
        parser.add_argument("--skip-purge", action="store_true",
                            help="Skip cache purge; only enable.")
        parser.add_argument(
            "--zone-resolver",
            default="",
            help="Optional dotted path to a callable `(domain, headers) -> zone_id | None`. "
                 "Defaults to live API lookup via /zones?name=<domain>.",
        )
        parser.add_argument("--sleep", type=float, default=0.3)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--json", dest="emit_json", action="store_true")
        parser.add_argument("--triggered-by", default="manual")

    def handle(self, *args, **options):
        from django.utils import timezone as tz

        from url_indexing_playbook.models import IndexingRun

        if options["skip_enable"] and options["skip_purge"]:
            raise CommandError(
                "--skip-enable and --skip-purge together leave nothing to do."
            )

        target_source = load_target_source(options["target_source"])
        slug_filter = parse_slugs(options["slugs"])
        dry_run = options["dry_run"]
        sleep_s = options["sleep"]

        targets = list(target_source.iter_targets(slugs=slug_filter))
        if not targets:
            raise CommandError("No targets matched the selected filters.")

        url_count = sum(len(t.urls) for t in targets)

        self.stdout.write(self.style.MIGRATE_HEADING("\nenable_crawler_hints"))
        self.stdout.write(
            f"  hosts={len(targets)}  urls={url_count}  "
            f"enable={not options['skip_enable']}  purge={not options['skip_purge']}  "
            f"dry_run={dry_run}"
        )
        self.stdout.write("")

        headers = None
        if not dry_run:
            try:
                headers = cf.build_auth_headers()
            except ValueError as e:
                raise CommandError(str(e)) from e

        zone_resolver = None
        if options["zone_resolver"]:
            zone_resolver = load_callable(options["zone_resolver"])

        run = IndexingRun.objects.create(
            command="enable_crawler_hints",
            status="running",
            target_count=len(targets),
            url_count=url_count,
            triggered_by=options["triggered_by"],
        )
        errors: list[dict] = []

        for t in targets:
            self.stdout.write(t.domain)
            zone_id = self._resolve_zone(t, headers, zone_resolver, dry_run, errors)
            if zone_id is None and not dry_run:
                continue

            if not options["skip_enable"]:
                self._enable(t, zone_id, headers, dry_run, run, errors)
                if sleep_s > 0 and not dry_run:
                    time.sleep(sleep_s)

            if not options["skip_purge"]:
                self._purge(t, zone_id, headers, dry_run, run, errors)
                if sleep_s > 0 and not dry_run:
                    time.sleep(sleep_s)

        run.status = "completed" if not errors else "failed"
        run.errors_json = errors
        run.finished_at = tz.now()
        run.save()

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Summary"))
        if not options["skip_enable"]:
            self.stdout.write(
                f"  Crawler Hints:  attempted={run.cloudflare_enable_attempted}  "
                f"ok={run.cloudflare_enable_ok}"
            )
        if not options["skip_purge"]:
            self.stdout.write(
                f"  Cache purge:    attempted={run.cloudflare_purge_attempted}  "
                f"ok={run.cloudflare_purge_ok}"
            )

        if options["emit_json"]:
            self.stdout.write("")
            self.stdout.write(json.dumps(_summary(run), indent=2, default=str))

    # ------------------------------------------------------------------

    def _resolve_zone(self, t, headers, custom_resolver, dry_run, errors):
        if dry_run:
            self.stdout.write(f"  [dry-run] resolve zone for {t.domain}")
            return "DRY-RUN-ZONE-ID"
        if custom_resolver:
            try:
                zone_id = custom_resolver(t.domain, headers)
            except Exception as e:  # noqa: BLE001
                errors.append({"phase": "zone_resolver", "domain": t.domain, "error": str(e)})
                self.stdout.write(self.style.ERROR(f"  ✗ zone resolver error: {e}"))
                return None
            if zone_id:
                return zone_id
        zone_id = cf.resolve_zone_id(t.domain, headers)
        if not zone_id:
            errors.append({"phase": "zone_resolve", "domain": t.domain, "error": "not found"})
            self.stdout.write(self.style.ERROR("  ✗ zone not found via API"))
            return None
        return zone_id

    def _enable(self, t, zone_id, headers, dry_run, run, errors):
        run.cloudflare_enable_attempted += 1
        if dry_run:
            self.stdout.write("  [dry-run] enable Crawler Hints")
            return
        result = cf.enable_crawler_hints(zone_id, headers)
        if result.get("ok"):
            run.cloudflare_enable_ok += 1
            self.stdout.write(
                f"  ✓ crawlhints_enabled={result.get('value')} "
                f"({result.get('status', '?')})"
            )
        else:
            errors.append({"phase": "cloudflare_enable", "domain": t.domain, "result": result})
            self.stdout.write(self.style.ERROR(
                f"  ✗ enable {result.get('status_code', 'ERR')}: "
                f"{result.get('body', result.get('error', ''))[:200]}"
            ))
        run.save(update_fields=["cloudflare_enable_attempted", "cloudflare_enable_ok"])

    def _purge(self, t, zone_id, headers, dry_run, run, errors):
        run.cloudflare_purge_attempted += 1
        if dry_run:
            self.stdout.write(f"  [dry-run] purge {len(t.urls)} URLs")
            return
        result = cf.purge_cache(zone_id, t.urls, headers)
        if result.get("ok"):
            run.cloudflare_purge_ok += 1
            self.stdout.write(f"  ✓ purged {result['url_count']} URLs")
        else:
            errors.append({"phase": "cloudflare_purge", "domain": t.domain, "result": result})
            self.stdout.write(self.style.ERROR(
                f"  ✗ purge {result.get('status_code', 'ERR')}: "
                f"{result.get('body', result.get('error', ''))[:200]}"
            ))
        run.save(update_fields=["cloudflare_purge_attempted", "cloudflare_purge_ok"])


def _summary(run):
    return {
        "command": run.command,
        "status": run.status,
        "target_count": run.target_count,
        "url_count": run.url_count,
        "cloudflare": {
            "enable": {
                "attempted": run.cloudflare_enable_attempted,
                "ok": run.cloudflare_enable_ok,
            },
            "purge": {
                "attempted": run.cloudflare_purge_attempted,
                "ok": run.cloudflare_purge_ok,
            },
        },
        "run_id": run.id,
    }
