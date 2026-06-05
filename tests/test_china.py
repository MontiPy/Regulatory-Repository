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


from connectors.china import build_body, enriched_stub_body, _merge_un_equivalent

def test_build_body_has_title_status_and_link():
    meta = {"cn_title": "汽车正面碰撞的乘员保护",
            "en_title": "Frontal collision occupant protection",
            "status": "in-force", "impl_date": "2015-01-01", "adopted_standard": "ECE R94"}
    body = build_body(meta, "GB 11551-2014", "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=ABC")
    assert "GB 11551-2014" in body
    assert "Frontal collision occupant protection" in body
    assert "In-force" in body or "in-force" in body
    assert "2015-01-01" in body
    assert "ECE R94" in body
    assert "newGbInfo?hcno=ABC" in body

def test_enriched_stub_body_notes_unresolved():
    body = enriched_stub_body("GB 99999", "https://example.test/x")
    assert "GB 99999" in body
    assert "official" in body.lower()

def test_merge_un_equivalent_unions_un_ref_only():
    assert _merge_un_equivalent(["UN R94"], "ECE R16") == ["UN R94", "UN R16"]
    assert _merge_un_equivalent(["UN R94"], "ISO 6487") == ["UN R94"]
    assert _merge_un_equivalent(["UN R94"], "ECE R94") == ["UN R94"]
    assert _merge_un_equivalent(["UN R94"], None) == ["UN R94"]


import frontmatter
from connectors.china import pull

def _make_manifest(tmp_path, entry):
    import yaml
    mpath = tmp_path / "cn.yaml"
    mpath.write_text(yaml.safe_dump({"region": "CN", "records": [entry]}, allow_unicode=True), encoding="utf-8")
    return mpath

def test_pull_preserves_tags_and_unions_equivalents(tmp_path, monkeypatch):
    dest = tmp_path / "regs"; dest.mkdir()
    existing = frontmatter.Post(
        "old body",
        id="cn-gb-11551-2014", title="Old spreadsheet title", region="CN",
        citation="GB 11551-2014", status="in-force",
        source_url="https://old", source_api="spreadsheet",
        tagging_status="llm-tagged", commodities=["Airbags"], systems=["Crashworthiness"],
        un_equivalent=["UN R94"], un_equivalent_ai=["UN R16"],
    )
    (dest / "cn-gb-11551-2014.md").write_text(frontmatter.dumps(existing), encoding="utf-8")

    import connectors.china as china
    list_html = (FIX / "std_list_gb11551.html").read_text(encoding="utf-8")
    detail_html = (FIX / "newGbInfo_gb11551.html").read_text(encoding="utf-8")
    monkeypatch.setattr(china, "RateLimitedSession", lambda **kw: FakeSession(list_html))
    monkeypatch.setattr(china, "fetch_detail", lambda session, hcno: detail_html)

    manifest = _make_manifest(tmp_path, {
        "id": "cn-gb-11551-2014", "gb_number": "GB 11551-2014", "source_url": "https://old",
    })
    pull(manifest, dest)

    post = frontmatter.load(dest / "cn-gb-11551-2014.md")
    assert post["source_api"] == "china"
    assert post["commodities"] == ["Airbags"]
    assert post["tagging_status"] == "llm-tagged"
    assert post["un_equivalent"] == ["UN R94"]
    assert post["un_equivalent_ai"] == ["UN R16"]
    assert "occupants" in post["title"]
    assert "Old spreadsheet title" in post.get("aliases", [])
    assert "newGbInfo" in post["source_url"]


def test_parse_detail_maps_feizhi_to_superseded():
    # 废止 (abolished/replaced) must map to the taxonomy status "superseded",
    # not an out-of-taxonomy "abolished" (regression: build rejected the latter).
    html = "<div>标准状态</div><div class='content'>废止</div><div>在线预览</div>"
    assert parse_detail(html)["status"] == "superseded"
