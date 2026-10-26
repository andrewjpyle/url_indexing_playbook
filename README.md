# url_indexing_playbook

> Ping search engines about your new URLs. Django management commands for **GSC URL Inspection + IndexNow + Cloudflare Crawler Hints.**

A Django reusable app for the operational task of "I just shipped 50 new URLs — tell Google, Bing, Yandex, and friends." Ships three focused management commands for the three sanctioned-ish paths, plus a markdown deeplink generator for the manual GSC fallback.

Extracted from a production rollout across dozens of sites. The unit tests mock every external call, so no capture of a live run ships with this repo.

## Status

`0.1.0.dev0` — alpha. Production-tested via the reference deploys, but the public package itself is brand new — expect minor breaking changes before 1.0. Pin tightly.

## What it does

Four commands, one focused operation each:

- **`ping_search_engines`** — GSC URL Inspection API ping + IndexNow direct submission to Bing/Yandex/Naver/Seznam/Yep. Skip either with `--no-gsc` / `--no-indexnow`.
- **`enable_crawler_hints`** — for Cloudflare-fronted sites: enable Crawler Hints (CF's own IndexNow integration) + bulk cache purge. No origin key file deploy needed.
- **`generate_gsc_checklist`** — markdown of clickable deeplinks to GSC's "Request Indexing" UI. The only path Google actually promises will queue your URL.

- **`sitemap_funnel`** — read-only. Finds each host's sitemap (the `Sitemap:` line in `robots.txt` first, `/sitemap.xml` as a fallback), counts its URLs, and prints that next to the number of URLs you queued. Fetches retry on HTTP 429/503 and honor `Retry-After` (capped at 6 seconds per wait).

Plus:

- **Pluggable `TargetSource` adapter** — works against the bundled CSV / settings-dict source out of the box, or plug in your own model with one class.
- **Pluggable `gsc_inspector` callable** — bring your own GSC client (the package doesn't ship one to keep auth complexity yours, not ours).
- **Cloudflare auth fallback** — modern scoped Bearer token AND legacy Global API Key both work transparently.
- **`IndexingRun` audit log** — every command run tracked with status, counts, errors.
- **`--dry-run` everywhere** — verify the plan before any external calls.

## What it deliberately doesn't do

- ❌ **Bundle a Google Search Console client.** Google auth is hard, libraries change, you probably already have one. The Quickstart (step 5) has a worked wrapper around `google-api-python-client` so you can be running in about 5 minutes.
- ❌ **Generate or submit sitemap.xml.** Different concern.
- ❌ **Crawl your site.** Bring your URL list; we ship it to the right APIs.
- ❌ **Track indexing performance over time.** Use Search Console / GA4 for that. The `IndexingRun` log only records *what was sent*.

## Why this exists

When you ship N new URLs on a programmatic SEO site, you want to surface them to search engines as fast as possible. Five sanctioned-ish paths exist:

1. **GSC URL Inspection API ping** — read-only officially, but it's the same endpoint the GSC tool uses and surfaces the URL
2. **IndexNow** (Bing / Yandex / Naver / Seznam / Yep) — direct API submission, requires `<key>.txt` at domain root
3. **Cloudflare Crawler Hints** — strictly better IndexNow path for CF-fronted sites; uses CF's own key, triggered by cache purge
4. **Sitemap submission** via `sitemaps.submit` — only effective if URLs are in `sitemap.xml`
5. **Manual "Request Indexing" in GSC UI** — the only path Google actually promises

This package handles 1, 2, 3, and 5. (4 is a different concern.) None of these have a clean Django package — most are SaaS or one-off scripts.

---

## Quickstart

### 1. Install

```bash
pip install url_indexing_playbook
```

### 2. Add to Django settings

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "url_indexing_playbook",
]

URL_INDEXING_TARGETS = {
    "site_a": {
        "domain": "example.com",
        "urls": [
            "https://example.com/about/",
            "https://example.com/blog/",
        ],
    },
    "site_b": {
        "domain": "b.example.com",
        "urls": ["https://b.example.com/"],
    },
}
```

### 3. Migrate

```bash
manage.py migrate url_indexing_playbook
```

### 4. Dry-run everything

```bash
manage.py ping_search_engines --dry-run
manage.py enable_crawler_hints --dry-run
manage.py generate_gsc_checklist --output checklist.md
```

### 5. Wire up your GSC inspector callable

The package ships without a GSC client to keep auth complexity yours. The simplest wrapper using `google-api-python-client`:

```python
# myapp/gsc.py
from google.auth import default
from googleapiclient.discovery import build

_service = None

def get_service():
    global _service
    if _service is None:
        creds, _ = default(scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
        _service = build("searchconsole", "v1", credentials=creds)
    return _service

def inspect(site_url: str, inspection_url: str) -> dict:
    """Returns dict with verdict / coverage_state / last_crawl_time."""
    response = get_service().urlInspection().index().inspect(body={
        "inspectionUrl": inspection_url,
        "siteUrl": site_url,
    }).execute()
    result = response.get("inspectionResult", {})
    index_status = result.get("indexStatusResult", {})
    return {
        "verdict": index_status.get("verdict"),
        "coverage_state": index_status.get("coverageState"),
        "last_crawl_time": index_status.get("lastCrawlTime"),
    }
```

Then:

```bash
manage.py ping_search_engines \
    --gsc-client-callable myapp.gsc.inspect \
    --indexnow-key $INDEXNOW_KEY
```

The wrapper uses Application Default Credentials (`google.auth.default`), so a service account or `gcloud auth application-default login` both work. Any callable with the same `(site_url, inspection_url) -> dict` signature is accepted.

---

## CLI reference

### `ping_search_engines`

GSC URL Inspection ping + IndexNow direct submission.

| Flag | Default | Notes |
|---|---|---|
| `--target-source` | `url_indexing_playbook.adapters.DefaultTargetSource` | Dotted path to a `TargetSource` |
| `--slugs` | (all) | Comma-separated slug filter |
| `--gsc` / `--no-gsc` | `--gsc` | Enable / skip GSC inspection |
| `--indexnow` / `--no-indexnow` | `--indexnow` | Enable / skip IndexNow |
| `--gsc-client-callable` | (required for GSC) | Dotted path to your GSC inspector callable |
| `--indexnow-key` | `$INDEXNOW_KEY` | IndexNow key. Required when IndexNow enabled. |
| `--output-checklist` | (auto) | Path to write the GSC manual fallback checklist. Default: `/tmp/gsc-checklist-<ts>.md`. |
| `--sleep` | `0.4` | Seconds between GSC API calls |
| `--dry-run` | `false` | Print plan, no external calls |
| `--json` | `false` | Emit JSON summary on stdout |
| `--triggered-by` | `manual` | Logged on the IndexingRun record |

### `enable_crawler_hints`

For Cloudflare-fronted sites only. Toggle Crawler Hints + bulk cache purge.

| Flag | Default | Notes |
|---|---|---|
| `--target-source` | `url_indexing_playbook.adapters.DefaultTargetSource` | |
| `--slugs` | (all) | |
| `--skip-enable` | `false` | Skip the Crawler Hints toggle (only purge) |
| `--skip-purge` | `false` | Skip cache purge (only enable) |
| `--zone-resolver` | (auto, live API) | Optional dotted path to a callable for zone-id lookup; defaults to live API |
| `--sleep` | `0.3` | Between CF API calls |
| `--dry-run`, `--json`, `--triggered-by` | | (same as above) |

Auth: reads `CLOUDFLARE_API_TOKEN` (Bearer, modern, preferred) OR `CLOUDFLARE_API_KEY` + `CLOUDFLARE_EMAIL` (Global Key, legacy). Either scheme works; modern token wins if both are set.

### `generate_gsc_checklist`

Markdown of clickable deeplinks to GSC's "Request Indexing" UI. No external API calls.

| Flag | Default | Notes |
|---|---|---|
| `--target-source` | `url_indexing_playbook.adapters.DefaultTargetSource` | |
| `--slugs` | (all) | |
| `--output` | `/tmp/gsc-checklist-<ts>.md` | Output path |

---

## The adapter pattern

The bundled `DefaultTargetSource` reads from `settings.URL_INDEXING_TARGETS` (dict) or a CSV file. For real projects, write a small adapter against your own model:

```python
from url_indexing_playbook.targets import IndexingTarget, TargetSource
from myapp.models import Site

class SiteTargetSource(TargetSource):
    def iter_targets(self, *, slugs=None):
        qs = Site.objects.filter(production_url__isnull=False, indexable=True)
        if slugs:
            qs = qs.filter(slug__in=slugs)
        for site in qs:
            yield IndexingTarget(
                slug=site.slug,
                domain=site.domain,
                urls=[f"{site.production_url}{path}" for path in site.priority_paths],
            )
```

Then:

```bash
manage.py ping_search_engines --target-source myapp.adapters.SiteTargetSource
```

The OSS package never sees your model — it only sees `IndexingTarget` dataclasses.

---

## The 5 paths cheat sheet

| Path | Coverage | Effort | Notes |
|---|---|---|---|
| 1. GSC URL Inspection API | Google | This pkg + your GSC client | Read-only officially; surfaces the URL |
| 2. IndexNow direct | Bing/Yandex/Naver/Seznam/Yep | This pkg + key file at domain root | Skip if you're on Cloudflare — use #3 |
| 3. Cloudflare Crawler Hints | Bing/Yandex/Naver/Seznam/Yep | This pkg, no key file | Strictly better than #2 if you're on CF |
| 4. Sitemap submission | Google | Different tool | Only works if URLs are in sitemap.xml |
| 5. Manual GSC UI request | Google | Click each link | The only path Google promises will queue |

---

## Roadmap

`0.1.0` (next):
- [x] Worked GSC client wrapper (Quickstart step 5)
- [ ] PyPI publish

`0.2.0` (planned):
- [ ] Sitemap.xml submission helper (path #4)
- [ ] Diff-mode for `ping_search_engines` (re-inspect after N days, report deltas)

`Later`:
- [ ] Bing Webmaster Tools direct API integration
- [ ] Yandex Webmaster API direct integration

---

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
git clone https://github.com/andrewjpyle/url_indexing_playbook.git
cd url_indexing_playbook
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check . && pytest -q
```

## License

MIT. See [LICENSE](LICENSE).

## Author

Built and maintained by [Andrew J. Pyle](https://andrewjpyle.com). Originally extracted from production infrastructure running URL-indexing rollouts across portfolio sites.

---

## Part of a larger system

`url_indexing_playbook` is one of the reusable pieces pulled out of a private, autonomous build
system and released on its own — the machine needed it, so it built it, and now
it's yours too, MIT-licensed.

See the rest of the parts → **https://autonomousaj.com/parts**
