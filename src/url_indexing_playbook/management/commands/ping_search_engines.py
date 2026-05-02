"""GSC URL Inspection ping + IndexNow direct submission.

Usage:
    manage.py ping_search_engines --dry-run
    manage.py ping_search_engines --slugs site_a,site_b
    manage.py ping_search_engines --no-indexnow --gsc-client-callable myapp.gsc.inspect
    manage.py ping_search_engines --indexnow-key $INDEXNOW_KEY --json
"""

import json
import os
import time

from django.core.management.base import BaseCommand, CommandError

from url_indexing_playbook import checklist as checklist_mod
from url_indexing_playbook import indexnow
from url_indexing_playbook.management.commands._common import (
    DEFAULT_TARGET_SOURCE,
    load_callable,
    load_target_source,
    parse_slugs,
)


class Command(BaseCommand):
    help = "Submit URLs to GSC URL Inspection API and IndexNow."

    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--target-source",
            default=DEFAULT_TARGET_SOURCE,
            help=f"Dotted path to a TargetSource (default: {DEFAULT_TARGET_SOURCE})",
        )
        parser.add_argument(
            "--slugs",
            default="",
            help='Comma-separated slug filter (e.g., "site_a,site_b").',
        )

        parser.add_argument(
            "--gsc",
            dest="gsc",
            action="store_true",
            default=True,
            help="Run GSC URL Inspection API (default: on).",
        )
        parser.add_argument(
            "--no-gsc",
            dest="gsc",
            action="store_false",
            help="Skip GSC URL Inspection API.",
        )
        parser.add_argument(
            "--gsc-client-callable",
            default="",
            help="Dotted path to a callable matching "
            "`(site_url, inspection_url) -> dict` for GSC inspection.",
        )

        parser.add_argument(
            "--indexnow",
            dest="indexnow",
            action="store_true",
            default=True,
            help="Run IndexNow submission (default: on).",
        )
        parser.add_argument(
            "--no-indexnow",
            dest="indexnow",
            action="store_false",
            help="Skip IndexNow submission.",
        )
        parser.add_argument(
            "--indexnow-key",
            default=os.environ.get("INDEXNOW_KEY", ""),
            help="IndexNow key. Defaults to $INDEXNOW_KEY.",
        )

        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--output-checklist",
            default="",
            help="Optional path for the GSC manual fallback checklist.",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.4,
            help="Seconds between GSC API calls (default 0.4).",
        )
        parser.add_argument(
            "--json",
            dest="emit_json",
            action="store_true",
            help="Emit a JSON summary on stdout.",
        )
        parser.add_argument("--triggered-by", default="manual")

    def handle(self, *args, **options):
        from django.utils import timezone as tz

        from url_indexing_playbook.models import IndexingRun

        target_source = load_target_source(options["target_source"])
        slug_filter = parse_slugs(options["slugs"])
        gsc_enabled = options["gsc"]
        indexnow_enabled = options["indexnow"]
        dry_run = options["dry_run"]
        sleep_s = options["sleep"]
        emit_json = options["emit_json"]

        targets = list(target_source.iter_targets(slugs=slug_filter))
        if not targets:
            raise CommandError("No targets matched the selected filters.")

        url_count = sum(len(t.urls) for t in targets)

        self.stdout.write(self.style.MIGRATE_HEADING("\nping_search_engines"))
        self.stdout.write(
            f"  hosts={len(targets)}  urls={url_count}  "
            f"gsc={gsc_enabled}  indexnow={indexnow_enabled}  dry_run={dry_run}"
        )
        self.stdout.write("")

        if gsc_enabled and not options["gsc_client_callable"] and not dry_run:
            raise CommandError(
                "GSC enabled but --gsc-client-callable is required for live runs. "
                "Pass --no-gsc to skip, or wire up a callable. See README."
            )

        if indexnow_enabled and not options["indexnow_key"] and not dry_run:
            raise CommandError(
                "IndexNow enabled but --indexnow-key is empty and "
                "$INDEXNOW_KEY is not set. Either pass --indexnow-key, "
                "set the env var, or pass --no-indexnow."
            )

        run = IndexingRun.objects.create(
            command="ping_search_engines",
            status="running",
            target_count=len(targets),
            url_count=url_count,
            triggered_by=options["triggered_by"],
        )
        errors: list[dict] = []

        # GSC inspection ----------------------------------------------------
        if gsc_enabled:
            self._run_gsc(
                targets, options["gsc_client_callable"], dry_run, sleep_s, run, errors,
            )

        # IndexNow ----------------------------------------------------------
        if indexnow_enabled:
            self._run_indexnow(
                targets, options["indexnow_key"], dry_run, run, errors,
            )

        # Manual GSC checklist (always) -------------------------------------
        checklist_path = checklist_mod.generate(targets, options["output_checklist"] or None)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Manual GSC fallback checklist: {checklist_path}"))

        # Finalize run record -----------------------------------------------
        run.status = "completed" if not errors else "failed"
        run.errors_json = errors
        run.finished_at = tz.now()
        run.save()

        # Summary -----------------------------------------------------------
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Summary"))
        if gsc_enabled:
            self.stdout.write(
                f"  GSC URL Inspection: attempted={run.gsc_attempted}  "
                f"ok={run.gsc_ok}  failed={run.gsc_failed}"
            )
        if indexnow_enabled:
            self.stdout.write(
                f"  IndexNow:           attempted={run.indexnow_attempted}  "
                f"ok={run.indexnow_ok}  "
                f"skipped_no_key_file={run.indexnow_skipped_no_key_file}  "
                f"failed={run.indexnow_failed}"
            )

        if emit_json:
            self.stdout.write("")
            self.stdout.write(json.dumps(_summary(run, checklist_path), indent=2, default=str))

    # ------------------------------------------------------------------

    def _run_gsc(self, targets, callable_path, dry_run, sleep_s, run, errors):
        self.stdout.write(self.style.MIGRATE_HEADING("GSC URL Inspection"))

        if dry_run:
            for t in targets:
                for url in t.urls:
                    self.stdout.write(f"  [dry-run] {t.effective_gsc_site_url}  {url}")
            return

        try:
            inspect = load_callable(callable_path)
        except Exception as e:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(f"  Could not load --gsc-client-callable: {e}"))
            errors.append({"phase": "gsc_load", "error": str(e)})
            return

        for t in targets:
            for url in t.urls:
                run.gsc_attempted += 1
                try:
                    result = inspect(site_url=t.effective_gsc_site_url, inspection_url=url)
                except Exception as e:  # noqa: BLE001
                    run.gsc_failed += 1
                    errors.append({"phase": "gsc", "url": url, "error": str(e)})
                    self.stdout.write(self.style.ERROR(
                        f"  ✗ {t.domain:36s}  {url}\n      {e}"
                    ))
                else:
                    run.gsc_ok += 1
                    verdict = (result or {}).get("verdict") or "?"
                    coverage = (result or {}).get("coverage_state") or "?"
                    last_crawl = (result or {}).get("last_crawl_time") or "never"
                    self.stdout.write(
                        f"  ✓ {t.domain:36s}  {url}\n"
                        f"      verdict={verdict}  coverage={coverage}  "
                        f"last_crawl={last_crawl}"
                    )
                if sleep_s > 0:
                    time.sleep(sleep_s)
        run.save(update_fields=["gsc_attempted", "gsc_ok", "gsc_failed"])

    def _run_indexnow(self, targets, key, dry_run, run, errors):
        self.stdout.write(self.style.MIGRATE_HEADING("IndexNow"))

        if dry_run:
            for t in targets:
                self.stdout.write(
                    f"  [dry-run] POST {indexnow.INDEXNOW_ENDPOINT}  "
                    f"host={t.domain}  urls={len(t.urls)}"
                )
            return

        for t in targets:
            run.indexnow_attempted += 1
            ok, msg = indexnow.probe_key_file(t.domain, key)
            if not ok:
                run.indexnow_skipped_no_key_file += 1
                self.stdout.write(self.style.WARNING(
                    f"  ⊘ {t.domain:36s}  skipped — key probe: {msg}"
                ))
                continue

            result = indexnow.submit(t.domain, key, t.urls)
            if result.get("ok"):
                run.indexnow_ok += 1
                self.stdout.write(
                    f"  ✓ {t.domain:36s}  {result['status_code']}  "
                    f"urls={result['url_count']}"
                )
            else:
                run.indexnow_failed += 1
                errors.append({"phase": "indexnow", "host": t.domain, "result": result})
                self.stdout.write(self.style.ERROR(
                    f"  ✗ {t.domain:36s}  {result.get('status_code', 'ERR')}  "
                    f"{result.get('body', result.get('error', ''))[:200]}"
                ))
        run.save(
            update_fields=[
                "indexnow_attempted", "indexnow_ok",
                "indexnow_failed", "indexnow_skipped_no_key_file",
            ]
        )


def _summary(run, checklist_path):
    return {
        "command": run.command,
        "status": run.status,
        "target_count": run.target_count,
        "url_count": run.url_count,
        "gsc": {
            "attempted": run.gsc_attempted,
            "ok": run.gsc_ok,
            "failed": run.gsc_failed,
        },
        "indexnow": {
            "attempted": run.indexnow_attempted,
            "ok": run.indexnow_ok,
            "failed": run.indexnow_failed,
            "skipped_no_key_file": run.indexnow_skipped_no_key_file,
        },
        "checklist_path": checklist_path,
        "run_id": run.id,
    }
