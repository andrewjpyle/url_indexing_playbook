"""Tests for sitemap discovery and 429 backoff. No network: requests.get is patched."""

from unittest.mock import MagicMock, patch

from django.core.management import call_command

from url_indexing_playbook import sitemaps

URLSET = (
    b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b"<url><loc>https://a.test/1</loc></url><url><loc>https://a.test/2</loc></url></urlset>"
)
INDEX = (
    b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b"<sitemap><loc>https://a.test/s1.xml</loc></sitemap></sitemapindex>"
)


def _resp(status=200, content=b"", text="", headers=None):
    r = MagicMock()
    r.status_code = status
    r.content = content
    r.text = text
    r.headers = headers or {}
    return r


def test_retries_429_and_honors_retry_after():
    sleeps = []
    with patch("requests.get", side_effect=[_resp(429, headers={"Retry-After": "3"}), _resp(200)]):
        resp = sitemaps.http_get("https://a.test/x", sleep=sleeps.append)
    assert resp.status_code == 200
    assert sleeps == [3.0]


def test_backoff_is_capped_and_defaults_to_exponential():
    sleeps = []
    seq = [_resp(503, headers={"Retry-After": "600"}), _resp(429), _resp(200)]
    with patch("requests.get", side_effect=seq):
        sitemaps.http_get("https://a.test/x", sleep=sleeps.append)
    assert sleeps == [sitemaps.MAX_BACKOFF_SECONDS, 4]


def test_returns_last_throttled_response_when_retries_run_out():
    sleeps = []
    with patch("requests.get", side_effect=[_resp(429)] * 3) as get:
        resp = sitemaps.http_get("https://a.test/x", sleep=sleeps.append)
    assert resp.status_code == 429
    assert get.call_count == 3
    assert len(sleeps) == 2


def test_non_retry_status_returns_immediately():
    with patch("requests.get", side_effect=[_resp(404)]) as get:
        assert sitemaps.http_get("https://a.test/x").status_code == 404
    assert get.call_count == 1


def test_robots_sitemap_directive_wins():
    robots = "User-agent: *\nSitemap: https://a.test/sitemap-index.xml\n"
    with patch("requests.get", return_value=_resp(200, text=robots)):
        assert sitemaps.resolve_sitemap_url("a.test") == "https://a.test/sitemap-index.xml"


def test_falls_back_to_sitemap_xml_without_directive():
    with patch("requests.get", return_value=_resp(200, text="User-agent: *\n")):
        assert sitemaps.resolve_sitemap_url("a.test") == "https://a.test/sitemap.xml"


def test_falls_back_when_robots_missing():
    with patch("requests.get", return_value=_resp(404)):
        assert sitemaps.resolve_sitemap_url("a.test") == "https://a.test/sitemap.xml"


def test_count_follows_sitemap_index():
    responses = {
        "https://a.test/robots.txt": _resp(200, text="Sitemap: https://a.test/idx.xml"),
        "https://a.test/idx.xml": _resp(200, content=INDEX),
        "https://a.test/s1.xml": _resp(200, content=URLSET),
    }
    with patch("requests.get", side_effect=lambda url, **kw: responses[url]):
        assert sitemaps.count_sitemap_urls("a.test") == 2


def test_sitemap_funnel_reports_counts(db, capsys):
    with patch("url_indexing_playbook.management.commands.sitemap_funnel.resolve_sitemap_url",
               return_value="https://x/sitemap.xml"), \
         patch("url_indexing_playbook.management.commands.sitemap_funnel.count_sitemap_urls",
               return_value=7):
        call_command("sitemap_funnel", "--slugs", "site_a")
    out = capsys.readouterr().out
    assert "sitemap=7" in out
    assert "queued=2" in out
