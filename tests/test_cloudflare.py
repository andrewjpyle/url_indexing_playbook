"""Tests for the Cloudflare module — auth, zone resolve, hints, purge."""

from unittest.mock import MagicMock, patch

import pytest

from url_indexing_playbook import cloudflare as cf


def _resp(status_code: int, json_body=None, text: str = "") -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.content = bool(json_body) or bool(text)
    r.json.return_value = json_body or {}
    return r


# ----------------------------------------------------------------------
# Auth header construction
# ----------------------------------------------------------------------


def test_auth_headers_prefer_token(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok-abc")
    monkeypatch.setenv("CLOUDFLARE_API_KEY", "should-be-ignored")
    monkeypatch.setenv("CLOUDFLARE_EMAIL", "x@y.com")
    headers = cf.build_auth_headers()
    assert headers["Authorization"] == "Bearer tok-abc"
    assert "X-Auth-Email" not in headers


def test_auth_headers_legacy_global_key(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.setenv("CLOUDFLARE_API_KEY", "key-123")
    monkeypatch.setenv("CLOUDFLARE_EMAIL", "x@y.com")
    headers = cf.build_auth_headers()
    assert headers["X-Auth-Key"] == "key-123"
    assert headers["X-Auth-Email"] == "x@y.com"
    assert "Authorization" not in headers


def test_auth_headers_explicit_kwargs_win(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "from-env")
    headers = cf.build_auth_headers(api_token="from-arg")
    assert headers["Authorization"] == "Bearer from-arg"


def test_auth_headers_no_creds_raises(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_EMAIL", raising=False)
    with pytest.raises(ValueError, match="No Cloudflare auth"):
        cf.build_auth_headers()


# ----------------------------------------------------------------------
# Zone resolution
# ----------------------------------------------------------------------


def test_resolve_zone_id_found():
    body = {"result": [{"id": "zone-abc", "name": "example.com"}]}
    with patch.object(cf.requests, "get", return_value=_resp(200, json_body=body)):
        assert cf.resolve_zone_id("example.com", {}) == "zone-abc"


def test_resolve_zone_id_not_in_results():
    body = {"result": [{"id": "zone-abc", "name": "other.com"}]}
    with patch.object(cf.requests, "get", return_value=_resp(200, json_body=body)):
        assert cf.resolve_zone_id("example.com", {}) is None


def test_resolve_zone_id_api_error():
    with patch.object(cf.requests, "get", return_value=_resp(500, text="oops")):
        assert cf.resolve_zone_id("example.com", {}) is None


# ----------------------------------------------------------------------
# Crawler Hints toggle
# ----------------------------------------------------------------------


def test_enable_crawler_hints_success():
    body = {"result": {"value": True, "status": "ok"}}
    with patch.object(cf.requests, "post", return_value=_resp(200, json_body=body)) as p:
        result = cf.enable_crawler_hints("zone-abc", {})
    assert result["ok"] is True
    assert result["value"] is True
    args, kwargs = p.call_args
    assert "/zones/zone-abc/flags/products/cache/changes" in args[0]
    assert kwargs["json"] == {"feature": "crawlhints_enabled", "value": True}


def test_enable_crawler_hints_failure():
    with patch.object(cf.requests, "post", return_value=_resp(400, text='{"error":"bad"}')):
        result = cf.enable_crawler_hints("zone-abc", {})
    assert result["ok"] is False
    assert result["status_code"] == 400


# ----------------------------------------------------------------------
# Cache purge
# ----------------------------------------------------------------------


def test_purge_cache_success():
    with patch.object(cf.requests, "post", return_value=_resp(200, json_body={"result": {}})) as p:
        result = cf.purge_cache(
            "zone-abc",
            ["https://x.com/", "https://x.com/y/"],
            {},
        )
    assert result["ok"] is True
    assert result["url_count"] == 2

    args, kwargs = p.call_args
    assert "/zones/zone-abc/purge_cache" in args[0]
    assert kwargs["json"] == {"files": ["https://x.com/", "https://x.com/y/"]}


def test_purge_cache_failure():
    with patch.object(cf.requests, "post", return_value=_resp(403, text="forbidden")):
        result = cf.purge_cache("zone-abc", ["https://x.com/"], {})
    assert result["ok"] is False
    assert result["status_code"] == 403
