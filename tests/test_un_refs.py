from scripts.un_refs import normalize_un, ece_id_to_un, scan_grounded_un

def test_normalize_un_canonicalizes_spacing_and_case():
    assert normalize_un("un r94") == "UN R94"
    assert normalize_un("UN R13H") == "UN R13H"
    assert normalize_un("R94") == "UN R94"
    assert normalize_un("UN R0") is None      # junk
    assert normalize_un("UN R94x") is None     # bad suffix
    assert normalize_un("garbage") is None

def test_ece_id_to_un_parses_ids():
    assert ece_id_to_un("ece-r94") == "UN R94"
    assert ece_id_to_un("ece-r13-h") == "UN R13H"
    assert ece_id_to_un("ece-r0") is None      # junk number
    assert ece_id_to_un("us-fmvss-208") is None

def test_scan_grounded_un_finds_only_un_ece_citations():
    body = (
        "This standard aligns with UN Regulation No. 94 and ECE R95. "
        "It references Regulation (EC) No 661/2009 which is NOT a UN reg. "
        "See also UN R0 (junk) and plain Regulation No. 12 (ambiguous)."
    )
    found = scan_grounded_un(body)
    assert found == ["UN R94", "UN R95"]   # sorted, deduped; EC/junk/ambiguous excluded

def test_scan_grounded_un_does_not_absorb_following_word_as_suffix():
    # Portuguese "e" (and) must not become a variant suffix on the prior number.
    found = scan_grounded_un("os requisitos UN R32, UN R34 e UN R94, conforme")
    assert found == ["UN R32", "UN R34", "UN R94"]
    # A genuine adjacent variant suffix is still captured.
    assert scan_grounded_un("per UN R13H brake rules") == ["UN R13H"]


def test_extract_writes_grounded_for_non_ece(tmp_path):
    import frontmatter
    from scripts.extract_un_equivalent import extract_for_record
    p = tmp_path / "us-fmvss-301.md"
    p.write_text(
        "---\nid: us-fmvss-301\nregion: US\ntitle: Fuel\n---\n"
        "Harmonized with UN Regulation No. 34 on fuel tanks.\n",
        encoding="utf-8",
    )
    changed = extract_for_record(p)
    assert changed is True
    assert frontmatter.load(p)["un_equivalent"] == ["UN R34"]

def test_extract_skips_ece_self_reference(tmp_path):
    import frontmatter
    from scripts.extract_un_equivalent import extract_for_record
    p = tmp_path / "ece-r94.md"
    p.write_text(
        "---\nid: ece-r94\nregion: ECE\ntitle: Frontal collision\n---\n"
        "This is UN Regulation No. 94 itself.\n",
        encoding="utf-8",
    )
    changed = extract_for_record(p)
    assert frontmatter.load(p).get("un_equivalent", []) == []
