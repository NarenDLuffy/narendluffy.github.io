from ingestion import http_cache


class R:
    def __init__(self, code, body=b"", headers=None):
        self.status_code, self.content, self.headers = code, body, headers or {}
        self.ok = code < 400


class S:
    def __init__(self):
        self.sent = []

    def get(self, url, timeout, headers):
        self.sent.append(headers)
        if headers.get("If-None-Match") == '"a"':
            return R(304)
        return R(200, b"doc", {"ETag": '"a"'})


def test_second_fetch_is_conditional_and_reuses_body(tmp_path, monkeypatch):
    monkeypatch.setattr(http_cache, "CACHE_DIR", tmp_path)
    s = S()
    assert http_cache.cached_get("https://x/y.docx", session=s) == b"doc"
    assert http_cache.cached_get("https://x/y.docx", session=s) == b"doc"
    assert s.sent[1]["If-None-Match"] == '"a"'
