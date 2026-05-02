# Contributing

Thanks for the interest. `url_indexing_playbook` is an early-stage project; PRs and issues are welcome but expect a real review before anything lands.

## Before you open a PR

- **Open an issue first** for non-trivial changes (anything beyond a typo, doc fix, or small bug). Discussion saves both of us time.
- **One concern per PR.** Prefer multiple small PRs over one giant one.
- **Match the existing style.** Ruff is the source of truth.

## Local setup

```bash
git clone https://github.com/andrewjpyle/url_indexing_playbook.git
cd url_indexing_playbook

uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Running the suite

```bash
ruff check .
pytest -q
```

CI runs on push and PR. Matrix: Python 3.10/3.11/3.12 × Django 4.2/5.0/5.1.

## Trying the demo

```bash
cd examples/states_of_matter
python manage.py migrate
python manage.py ping_search_engines --dry-run
python manage.py enable_crawler_hints --dry-run
python manage.py generate_gsc_checklist
```

## What kinds of changes land easily

- Bug fixes with a regression test.
- DX improvements with no API change (better error messages, clearer help text).
- Documentation tightening.
- New optional features with `--flag` opt-in (no behavior change for existing users).

## What kinds of changes need discussion first

- API surface changes to `TargetSource`, `IndexingTarget`, the management commands' flags, or the `IndexingRun` model.
- New runtime dependencies.
- Adding non-Django frameworks (this is on the roadmap but warrants a design discussion).
- Bundling a GSC client (deliberately not bundled — see README).

## Commit messages

Conventional Commits style preferred but not enforced.

## License

By contributing, you agree your work ships under the [MIT license](LICENSE).
