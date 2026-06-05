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


from connectors.china import parse_detail

def test_parse_detail_real_fixture():
    html = (FIX / "newGbInfo_gb11551.html").read_text(encoding="utf-8")
    meta = parse_detail(html)
    assert meta["en_title"] == "The protection of the occupants in the event of a frontal collision for motor vehicle"
    assert meta["cn_title"] == "汽车正面碰撞的乘员保护"
    assert meta["status"] == "in-force"
    assert meta["impl_date"] == "2015-01-01"
    assert meta["adopted_standard"] is None  # this record declares none

def test_parse_detail_extracts_adopted_standard():
    # Minimal crafted snippet exercising the (sparsely populated) adopted-standard row.
    html = "<div>采用国际标准</div><div class='content'>ECE R94 (MOD)</div><div>主管部门</div>"
    meta = parse_detail(html)
    assert meta["adopted_standard"] == "ECE R94"

def test_parse_detail_missing_fields_are_none():
    meta = parse_detail("<html><body>nothing here</body></html>")
    assert meta["en_title"] is None
    assert meta["status"] is None
