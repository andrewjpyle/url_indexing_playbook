"""Tests for IndexNow submission + key-file probe."""

from unittest.mock import MagicMock, patch

from url_indexing_playbook import indexnow


def _resp(status_code: int, text: str = "") -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    return r


def test_probe_key_file_head_200():
    with patch.object(indexnow.requests, "head", return_value=_resp(200)):
        ok, msg = indexnow.probe_key_file("example.com", "abc123")
    assert ok is True
    assert msg == "200"


def test_probe_key_file_falls_back_to_get_when_head_405():
    with patch.object(indexnow.requests, "head", return_value=_resp(405)) as h, \
         patch.object(indexnow.requests, "get", return_value=_resp(200, "abc123")) as g:
        ok, msg = indexnow.probe_key_file("example.com", "abc123")
    assert ok is True
    assert "GET" in msg
    h.assert_called_once()
    g.assert_called_once()


def test_probe_key_file_get_body_mismatch():
    with patch.object(indexnow.requests, "head", return_value=_resp(403)), \
         patch.object(indexnow.requests, "get", return_value=_resp(200, "wrong-key")):
        ok, msg = indexnow.probe_key_file("example.com", "abc123")
    assert ok is False
    assert "does not match" in msg


def test_probe_key_file_404():
    with patch.object(indexnow.requests, "head", return_value=_resp(404)):
        ok, msg = indexnow.probe_key_file("example.com", "abc123")
    assert ok is False
    assert "404" in msg


def test_submit_success():
    with patch.object(indexnow.requests, "post", return_value=_resp(200)) as p:
        result = indexnow.submit("example.com", "k", ["https://example.com/x/"])
    assert result["ok"] is True
    assert result["status_code"] == 200
    assert result["url_count"] == 1

    args, kwargs = p.call_args
    assert args[0] == indexnow.INDEXNOW_ENDPOINT
    payload = kwargs["json"]
    assert payload["host"] == "example.com"
    assert payload["key"] == "k"
    assert payload["keyLocation"] == "https://example.com/k.txt"
    assert payload["urlList"] == ["https://example.com/x/"]


def test_submit_failure_includes_body():
    with patch.object(indexnow.requests, "post", return_value=_resp(422, "bad key")):
        result = indexnow.submit("example.com", "k", ["https://example.com/"])
    assert result["ok"] is False
    assert result["status_code"] == 422
    assert result["body"] == "bad key"


def test_submit_request_exception():
    import requests as real_requests

    def boom(*a, **kw):
        raise real_requests.RequestException("network down")

    with patch.object(indexnow.requests, "post", side_effect=boom):
        result = indexnow.submit("example.com", "k", ["https://example.com/"])
    assert result["ok"] is False
    assert "network down" in result["error"]
