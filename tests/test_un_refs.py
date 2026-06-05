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
