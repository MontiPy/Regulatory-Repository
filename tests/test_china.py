from pathlib import Path
from connectors.china import search_hcno

FIX = Path(__file__).parent / "fixtures" / "china"

class FakeResp:
    def __init__(self, text): self.text = text; self.encoding = "utf-8"
    def raise_for_status(self): pass

class FakeSession:
    """Returns a fixed page for any .get(), recording the URL."""
    def __init__(self, text): self._text = text; self.urls = []
    def get(self, url, **kw): self.urls.append(url); return FakeResp(self._text)
    def close(self): pass

def test_search_hcno_exact_version():
    html = (FIX / "std_list_gb11551.html").read_text(encoding="utf-8")
    session = FakeSession(html)
    hcno, label = search_hcno(session, "GB 11551-2014")
    assert hcno == "290A78A7D1665437A160104DCE7FA380"
    assert label == "GB 11551-2014"

def test_search_hcno_returns_none_when_absent():
    session = FakeSession("<html><body>no results</body></html>")
    assert search_hcno(session, "GB 99999-2099") is None
