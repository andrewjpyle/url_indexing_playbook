"""IndexNow direct submission. Pure HTTP; no Django required.

IndexNow notifies Bing, Yandex, Naver, Seznam, Yep when content changes.
Requires a `<key>.txt` file deployed at each domain root.
"""

import requests

INDEXNOW_ENDPOINT = "https://api.indexnow.org/IndexNow"


def probe_key_file(host: str, key: str, *, timeout: float = 8.0) -> tuple[bool, str]:
    """Verify https://<host>/<key>.txt is reachable and matches the expected key.

    HEAD probe with GET fallback (some hosts disallow HEAD). Returns (ok, status_msg).
    """
    key_url = f"https://{host}/{key}.txt"
    try:
        r = requests.head(key_url, timeout=timeout, allow_redirects=True)
        if r.status_code in (405, 403):
            r = requests.get(key_url, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                body = (r.text or "").strip()
                if body == key:
                    return True, "200 (GET, body match)"
                return False, "200 but body does not match expected key"
            return False, f"GET {r.status_code}"
        if r.status_code == 200:
            return True, "200"
        return False, f"HEAD {r.status_code}"
    except requests.RequestException as e:
        return False, f"probe error: {e}"


def submit(
    host: str,
    key: str,
    urls: list[str],
    *,
    timeout: float = 15.0,
) -> dict:
    """POST to IndexNow. Returns a dict with `ok`, `status_code`, optional `body`.

    Caller is responsible for probing the key file first if they want to
    avoid wasted submissions.
    """
    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"https://{host}/{key}.txt",
        "urlList": urls,
    }
    try:
        resp = requests.post(
            INDEXNOW_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=timeout,
        )
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}

    ok = 200 <= resp.status_code < 300
    result: dict = {
        "ok": ok,
        "status_code": resp.status_code,
        "host": host,
        "url_count": len(urls),
    }
    if not ok:
        result["body"] = resp.text[:300]
    return result
