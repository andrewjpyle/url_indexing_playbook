"""Sitemap discovery and counting, with bounded backoff on rate limits.

Two lessons from running this against dozens of Cloudflare-fronted hosts:

* A burst of sitemap fetches draws HTTP 429/503. A couple of short retries that honor
  `Retry-After` turn those throttles into successful fetches.
* `/sitemap.xml` is only a guess. A site can declare its real sitemap (for example
  `/sitemap-index.xml`) in `robots.txt`, so read the `Sitemap:` directive first.
"""

import time
import xml.etree.ElementTree as ET

import requests

USER_AGENT = "url-indexing-playbook/0.1"
RETRY_STATUSES = (429, 503)
# Longest single sleep, in seconds. A large honored Retry-After across many hosts
# would otherwise stall the whole run.
MAX_BACKOFF_SECONDS = 6
_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def http_get(url: str, *, timeout: float = 20, retries: int = 2, sleep=time.sleep):
    """GET with bounded backoff on 429/503, honoring a numeric `Retry-After`.

    Without a usable header the wait is 2s, then 4s. Returns the last response when
    every attempt is throttled, so the caller sees the status code.
    """
    resp = None
    for attempt in range(retries + 1):
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if resp.status_code not in RETRY_STATUSES or attempt == retries:
            return resp
        wait = None
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                wait = float(retry_after)
            except ValueError:
                wait = None  # an HTTP-date form is not honored; use the default backoff
        if wait is None:
            wait = 2 ** (attempt + 1)
        sleep(min(wait, MAX_BACKOFF_SECONDS))
    return resp


def resolve_sitemap_url(domain: str, *, sleep=time.sleep) -> str:
    """Return the first `Sitemap:` URL in robots.txt, else `https://<domain>/sitemap.xml`."""
    try:
        resp = http_get(f"https://{domain}/robots.txt", timeout=15, sleep=sleep)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    candidate = line.split(":", 1)[1].strip()
                    if candidate.startswith("http"):
                        return candidate
    except requests.RequestException:
        pass
    return f"https://{domain}/sitemap.xml"


def count_sitemap_urls(domain: str, *, sleep=time.sleep) -> int:
    """Count `<url>` entries for a domain, following one level of sitemap index.

    A child sitemap that fails to load is skipped, so the count can be low for an
    index with broken children. Raises `requests.HTTPError` if the top-level
    sitemap itself does not load.
    """
    resp = http_get(resolve_sitemap_url(domain, sleep=sleep), timeout=30, sleep=sleep)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    children = root.findall("sm:sitemap", _NS)
    if not children:
        return len(root.findall("sm:url", _NS))
    total = 0
    for child in children:
        loc = child.find("sm:loc", _NS)
        if loc is None or not loc.text:
            continue
        try:
            sub = http_get(loc.text.strip(), timeout=30, sleep=sleep)
            if sub.status_code == 200:
                total += len(ET.fromstring(sub.content).findall("sm:url", _NS))
        except (requests.RequestException, ET.ParseError):
            continue
    return total
