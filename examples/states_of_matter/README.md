# Demo: states of matter

A 5-target reference demo. Five fictional sites (`solid.example.com`, `liquid.example.com`, etc.), each with two URLs. Runs the three commands in `--dry-run` mode against fake domains so you can see exactly what real-mode would do.

## Run the demo

From this directory:

```bash
# Install (in your active env)
pip install url_indexing_playbook
# (or: pip install -e ../.. if you're working from the repo)

# Migrate the demo's SQLite DB (for the IndexingRun audit log)
python manage.py migrate

# 1. Dry-run the GSC + IndexNow path
python manage.py ping_search_engines --dry-run

# 2. Dry-run the Cloudflare path
python manage.py enable_crawler_hints --dry-run

# 3. Generate the manual GSC fallback checklist (no dry-run needed; pure markdown)
python manage.py generate_gsc_checklist --output ./checklist.md
cat checklist.md
```

## Output

```
$ python manage.py ping_search_engines --dry-run

ping_search_engines
  hosts=5  urls=10  gsc=True  indexnow=True  dry_run=True

GSC URL Inspection
  [dry-run] sc-domain:solid.example.com  https://solid.example.com/
  [dry-run] sc-domain:solid.example.com  https://solid.example.com/about/
  ...

IndexNow
  [dry-run] POST https://api.indexnow.org/IndexNow  host=solid.example.com  urls=2
  [dry-run] POST https://api.indexnow.org/IndexNow  host=liquid.example.com  urls=2
  ...

Manual GSC fallback checklist: /tmp/gsc-checklist-2026-05-02T12-34-56.md
```

## Going live

Out of the box this demo is dry-run-only because the example URLs are fake. To run live against your own URLs:

1. Replace `URL_INDEXING_TARGETS` in `settings.py` with your real domains and URLs.
2. **For the GSC path**: write a small `gsc_inspector` callable using `google-api-python-client` (see [`docs/gsc-client-injection.md`](../../docs/gsc-client-injection.md), or the README quickstart).
3. **For IndexNow**: deploy `<key>.txt` at each domain root, then set `INDEXNOW_KEY` env var.
4. **For Cloudflare Crawler Hints**: set `CLOUDFLARE_API_TOKEN` (or legacy `CLOUDFLARE_API_KEY` + `CLOUDFLARE_EMAIL`).

Then drop `--dry-run` from any of the commands.

## What this demo demonstrates

- The bundled `DefaultTargetSource` works without writing any adapter code (just populate `URL_INDEXING_TARGETS`)
- All three commands run cleanly without external dependencies on real APIs
- The `IndexingRun` audit log records every invocation
- The markdown checklist is genuinely useful (not just a stub)

## Next: write your own adapter

For any real project you'll have a Django model — say `Site`, `Project`, `Domain` — and you don't want to hand-edit a settings dict. See the [adapter pattern walkthrough](../../README.md#the-adapter-pattern) in the main README.
