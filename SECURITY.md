# Security policy

## Supported versions

Pre-1.0, only the latest published version is supported. Security fixes will land in patch releases against the current minor.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security-sensitive reports.

Email: **andrew@andrewjpyle.com** with the subject line `[url_indexing_playbook SECURITY]`.

Include:

- A description of the vulnerability and its impact
- Steps to reproduce
- Affected version(s)
- Whether you'd like to be credited in the release notes

You should expect:

- An acknowledgement within ~3 business days
- A public fix released as soon as practical (typically within 14 days for non-critical issues, faster for actively exploitable ones)
- Credit in the release notes if you want it

## Scope

In scope:

- The Python package itself (`src/url_indexing_playbook/`)
- The management commands' argument parsing
- IndexNow + Cloudflare HTTP request construction (injection, payload integrity)
- The default Cloudflare auth header builder

Out of scope:

- Vulnerabilities in user-supplied `TargetSource` adapters or GSC client callables
- Issues only reproducible with a malicious `INDEXNOW_KEY` or Cloudflare credentials — those are auth boundary problems, not package problems
- Vulnerabilities in transitive dependencies that don't affect this package's surface
- Submission failures upstream at IndexNow / Cloudflare / GSC due to API changes (those are integration issues, file as bugs)
