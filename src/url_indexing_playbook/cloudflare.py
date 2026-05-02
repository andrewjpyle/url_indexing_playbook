"""Cloudflare Crawler Hints + cache purge. Pure HTTP; no Django required."""

import os

import requests

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


def build_auth_headers(
    *,
    api_token: str | None = None,
    api_key: str | None = None,
    email: str | None = None,
) -> dict:
    """Return Cloudflare auth headers based on what's available.

    Two supported schemes:
      1. Scoped API Token (modern, preferred):
         CLOUDFLARE_API_TOKEN  ->  Authorization: Bearer ...
      2. Global API Key (legacy):
         CLOUDFLARE_API_KEY + CLOUDFLARE_EMAIL  ->
         X-Auth-Email + X-Auth-Key

    Modern token wins if both are set. Reads from explicit kwargs first,
    then env vars.
    """
    token = (api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "")).strip()
    if token:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    key = (api_key or os.environ.get("CLOUDFLARE_API_KEY", "")).strip()
    addr = (email or os.environ.get("CLOUDFLARE_EMAIL", "")).strip()
    if key and addr:
        return {
            "X-Auth-Email": addr,
            "X-Auth-Key": key,
            "Content-Type": "application/json",
        }

    raise ValueError(
        "No Cloudflare auth configured. Set CLOUDFLARE_API_TOKEN, OR ensure "
        "both CLOUDFLARE_API_KEY and CLOUDFLARE_EMAIL are set for legacy auth."
    )


def resolve_zone_id(
    domain: str,
    headers: dict,
    *,
    timeout: float = 10.0,
) -> str | None:
    """Look up a zone ID via live API. Returns None if not found."""
    try:
        resp = requests.get(
            f"{CLOUDFLARE_API_BASE}/zones",
            headers=headers,
            params={"name": domain},
            timeout=timeout,
        )
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None
    data = resp.json() if resp.content else {}
    if not isinstance(data, dict):
        return None
    for zone in data.get("result", []) or []:
        if zone.get("name") == domain:
            return zone.get("id")
    return None


def enable_crawler_hints(
    zone_id: str,
    headers: dict,
    *,
    timeout: float = 15.0,
) -> dict:
    """Enable Cloudflare Crawler Hints (IndexNow integration) for a zone.

    The right endpoint is `POST /zones/{id}/flags/products/cache/changes` with
    `{"feature": "crawlhints_enabled", "value": true}` — NOT the documented
    `/zones/{id}/settings/crawler_hints` (which 1006s with "Unrecognized zone
    setting name"). The flags-based endpoint is what the dashboard actually
    calls when you toggle Crawler Hints.
    """
    url = f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/flags/products/cache/changes"
    body = {"feature": "crawlhints_enabled", "value": True}

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}

    if 200 <= resp.status_code < 300:
        data = resp.json() if resp.content else {}
        result = (data.get("result") or {}) if isinstance(data, dict) else {}
        return {
            "ok": True,
            "status_code": resp.status_code,
            "value": result.get("value"),
            "status": result.get("status"),
        }
    return {
        "ok": False,
        "status_code": resp.status_code,
        "body": resp.text[:300],
    }


def purge_cache(
    zone_id: str,
    urls: list[str],
    headers: dict,
    *,
    timeout: float = 30.0,
) -> dict:
    """POST /zones/{id}/purge_cache with {"files": [...]}.

    Purging the cache is what triggers Crawler Hints to ping IndexNow for
    those URLs — without a content-fingerprint change, Cloudflare has no
    event to fire on.
    """
    url = f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/purge_cache"

    try:
        resp = requests.post(url, headers=headers, json={"files": urls}, timeout=timeout)
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}

    if 200 <= resp.status_code < 300:
        return {
            "ok": True,
            "status_code": resp.status_code,
            "url_count": len(urls),
        }
    return {
        "ok": False,
        "status_code": resp.status_code,
        "body": resp.text[:300],
    }
