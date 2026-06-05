import frontmatter
from connectors.india import canonical_url, build_body, pull

def test_canonical_url_rewrites_morth_domain():
    assert canonical_url("https://morth.nic.in/sites/default/files/ASI/AIS-156.pdf") == \
        "https://morth.gov.in/sites/default/files/ASI/AIS-156.pdf"
    assert canonical_url("https://morth.nic.in") == "https://morth.gov.in"
    assert canonical_url("https://www.araiindia.com/certification") == \
        "https://www.araiindia.com/certification"
    assert canonical_url("") == ""

def test_build_body_has_citation_framework_note_and_link():
    body = build_body("AIS-156", "EV battery safety", "https://morth.gov.in/x")
    assert "AIS-156" in body
    assert "EV battery safety" in body
    assert "CMVR" in body and "AIS" in body
    assert "https://morth.gov.in/x" in body

def _manifest(tmp_path, entry):
    import yaml
    mp = tmp_path / "in.yaml"
    mp.write_text(yaml.safe_dump({"region": "IN", "records": [entry]}, allow_unicode=True), encoding="utf-8")
    return mp

def test_pull_repoints_and_preserves(tmp_path):
    dest = tmp_path / "regs"; dest.mkdir()
    existing = frontmatter.Post(
        "old body", id="in-ais-038-rev-2-ais-156", title="EV battery safety", region="IN",
        citation="AIS-038 Rev.2 / AIS-156", status="in-force",
        source_url="https://morth.nic.in/sites/default/files/ASI/AIS-156.pdf",
        source_api="spreadsheet", tagging_status="llm-tagged", commodities=["Battery"],
        paywall=True, un_equivalent=["UN R100"], un_equivalent_ai=["UN R10"],
    )
    (dest / "in-ais-038-rev-2-ais-156.md").write_text(frontmatter.dumps(existing), encoding="utf-8")

    manifest = _manifest(tmp_path, {
        "id": "in-ais-038-rev-2-ais-156", "citation": "AIS-038 Rev.2 / AIS-156",
        "source_url": "https://morth.nic.in/sites/default/files/ASI/AIS-156.pdf",
    })
    pull(manifest, dest)

    post = frontmatter.load(dest / "in-ais-038-rev-2-ais-156.md")
    assert post["source_api"] == "ais"
    assert post["source_url"] == "https://morth.gov.in/sites/default/files/ASI/AIS-156.pdf"
    assert post["commodities"] == ["Battery"]
    assert post["tagging_status"] == "llm-tagged"
    assert post["paywall"] is True
    assert post["un_equivalent"] == ["UN R100"]
    assert post["un_equivalent_ai"] == ["UN R10"]
    assert post["title"] == "EV battery safety"
