# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- _(nothing yet)_

## [0.1.0.dev0] — initial scaffold

The first cut. Alpha — the API surface is settling and may shift before 0.1.0.

### Added
- **`TargetSource` adapter contract** with `IndexingTarget` dataclass.
- **`DefaultTargetSource`** — reads from `settings.URL_INDEXING_TARGETS` (dict) or a CSV file.
- **`IndexingRun` model** for per-invocation audit logging.
- **`ping_search_engines`** management command — GSC URL Inspection ping (callable injection) + IndexNow direct submission.
- **`enable_crawler_hints`** management command — Cloudflare Crawler Hints toggle + bulk cache purge.
- **`generate_gsc_checklist`** management command — markdown deeplink fallback for the manual GSC "Request Indexing" UI.
- **Cloudflare auth fallback** — modern Bearer token (CLOUDFLARE_API_TOKEN) AND legacy Global Key (CLOUDFLARE_API_KEY + CLOUDFLARE_EMAIL) both work transparently.
- **IndexNow key-file probe** with HEAD-then-GET fallback for hosts that disallow HEAD.
- **Reference demo** (`examples/states_of_matter/`) — runs all three commands in `--dry-run` mode against 5 dummy URLs.
- **Test suite** — 39 tests covering targets, IndexNow, Cloudflare, checklist, and end-to-end command flows.
- **CI workflow** — Python 3.10/3.11/3.12 × Django 4.2/5.0/5.1 matrix on GitHub Actions.

[Unreleased]: https://github.com/andrewjpyle/url_indexing_playbook/compare/v0.1.0.dev0...HEAD
[0.1.0.dev0]: https://github.com/andrewjpyle/url_indexing_playbook/releases/tag/v0.1.0.dev0
