from connectors.gulf import master_pdf_live, MASTER_URL

class FakeResp:
    def __init__(self, ct="application/pdf", status=200):
        self.headers = {"Content-Type": ct}; self.status_code = status; self.encoding = "utf-8"
    def raise_for_status(self): pass

class FakeSession:
    def __init__(self, resp=None, raises=False):
        self._resp = resp or FakeResp(); self._raises = raises; self.urls = []
    def get(self, url, **kw):
        self.urls.append(url)
        if self._raises:
            raise RuntimeError("boom")
        return self._resp
    def close(self): pass

def test_master_pdf_live_true_for_pdf_200():
    assert master_pdf_live(FakeSession(FakeResp("application/pdf", 200))) is True

def test_master_pdf_live_false_for_404():
    assert master_pdf_live(FakeSession(FakeResp("text/html", 404))) is False

def test_master_pdf_live_false_on_exception():
    assert master_pdf_live(FakeSession(raises=True)) is False

from connectors.gulf import build_body

def test_build_body_links_master_when_reachable():
    body = build_body("GSO 1053:2002", "Brake hoses", MASTER_URL, reachable=True)
    assert "GSO 1053:2002" in body
    assert "Brake hoses" in body
    assert MASTER_URL in body
    assert "sold" in body.lower()

def test_build_body_notes_unavailable_when_unreachable():
    body = build_body("GSO 1053:2002", "Brake hoses", "https://fallback.example/x", reachable=False)
    assert "GSO 1053:2002" in body
    assert "https://fallback.example/x" in body
    assert "could not be reached" in body.lower()

import frontmatter
from connectors.gulf import pull

def _manifest(tmp_path, entry):
    import yaml
    mp = tmp_path / "gcc.yaml"
    mp.write_text(yaml.safe_dump({"region": "GCC", "records": [entry]}, allow_unicode=True), encoding="utf-8")
    return mp

def test_pull_repoints_url_and_preserves_tags_equivalents(tmp_path, monkeypatch):
    dest = tmp_path / "regs"; dest.mkdir()
    existing = frontmatter.Post(
        "old stub body",
        id="gcc-gso-1053-2002", title="Brake hoses", region="GCC",
        citation="GSO 1053:2002", status="in-force",
        source_url="https://www.gso.org.sa/wp-content/dead.pdf", source_api="spreadsheet",
        tagging_status="llm-tagged", commodities=["Brakes"], paywall=True,
        un_equivalent=["UN R90"], un_equivalent_ai=["UN R13"],
    )
    (dest / "gcc-gso-1053-2002.md").write_text(frontmatter.dumps(existing), encoding="utf-8")

    import connectors.gulf as gulf
    monkeypatch.setattr(gulf, "RateLimitedSession", lambda **kw: FakeSession(FakeResp("application/pdf", 200)))

    manifest = _manifest(tmp_path, {
        "id": "gcc-gso-1053-2002", "citation": "GSO 1053:2002",
        "source_url": "https://www.gso.org.sa/wp-content/dead.pdf",
    })
    pull(manifest, dest)

    post = frontmatter.load(dest / "gcc-gso-1053-2002.md")
    assert post["source_api"] == "gso"
    assert post["source_url"] == gulf.MASTER_URL
    assert post["commodities"] == ["Brakes"]
    assert post["tagging_status"] == "llm-tagged"
    assert post["paywall"] is True
    assert post["un_equivalent"] == ["UN R90"]
    assert post["un_equivalent_ai"] == ["UN R13"]
    assert post["title"] == "Brake hoses"


from connectors.gulf import is_gso_record

def test_is_gso_record_distinguishes_member_state_records():
    assert is_gso_record("GSO 1053:2002", "https://www.gso.org.sa/wp-content/x.pdf") is True
    assert is_gso_record("GSO 36:2005", "https://other.example/x") is True       # GSO citation
    assert is_gso_record("SASO 2847", "https://www.saso.gov.sa/x") is False       # Saudi standard
    assert is_gso_record("UAE.S 5019:2024", "https://uaelegislation.gov.ae/x") is False
    assert is_gso_record("ECAS / MOIAT Conformity Certificates", "https://moiat.gov.ae/x") is False

def test_pull_skips_non_gso_record(tmp_path, monkeypatch):
    dest = tmp_path / "regs"; dest.mkdir()
    before = frontmatter.Post(
        "uae body", id="gcc-uae-s-5019-2024", title="UAE.S 5019:2024", region="GCC",
        citation="UAE.S 5019:2024", status="in-force",
        source_url="https://uaelegislation.gov.ae/x", source_api="spreadsheet",
        tagging_status="llm-tagged",
    )
    (dest / "gcc-uae-s-5019-2024.md").write_text(frontmatter.dumps(before), encoding="utf-8")
    import connectors.gulf as gulf
    monkeypatch.setattr(gulf, "RateLimitedSession", lambda **kw: FakeSession(FakeResp("application/pdf", 200)))
    mp = _manifest(tmp_path, {"id": "gcc-uae-s-5019-2024", "citation": "UAE.S 5019:2024",
                              "source_url": "https://uaelegislation.gov.ae/x"})
    gulf.pull(mp, dest)
    post = frontmatter.load(dest / "gcc-uae-s-5019-2024.md")
    assert post["source_api"] == "spreadsheet"          # untouched
    assert post["source_url"] == "https://uaelegislation.gov.ae/x"


def test_pull_preserves_existing_curated_body(tmp_path, monkeypatch):
    dest = tmp_path / "regs"; dest.mkdir()
    curated = ("# Protection against unauthorized use\n\n**Regulated Area:** Immobilizer\n\n"
               "## Key Compliance Intent\n\nReduce theft and unintended movement.\n")
    existing = frontmatter.Post(
        curated, id="gcc-gso-1053-2002", title="Theft protection", region="GCC",
        citation="GSO 1053:2002", status="in-force", source_url="https://old",
        source_api="spreadsheet", tagging_status="llm-tagged", paywall=True, un_equivalent=["UN R90"],
    )
    (dest / "gcc-gso-1053-2002.md").write_text(frontmatter.dumps(existing), encoding="utf-8")
    import connectors.gulf as gulf
    monkeypatch.setattr(gulf, "RateLimitedSession", lambda **kw: FakeSession(FakeResp("application/pdf", 200)))
    mp = _manifest(tmp_path, {"id": "gcc-gso-1053-2002", "citation": "GSO 1053:2002", "source_url": "https://old"})
    gulf.pull(mp, dest)
    post = frontmatter.load(dest / "gcc-gso-1053-2002.md")
    assert "Key Compliance Intent" in post.content      # curated body preserved
    assert "Regulated Area" in post.content
    assert post["source_url"] == gulf.MASTER_URL        # frontmatter still repointed
    assert post["un_equivalent"] == ["UN R90"]
