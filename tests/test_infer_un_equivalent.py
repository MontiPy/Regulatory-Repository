from scripts.infer_un_equivalent import build_prompt, parse_ai_equiv

VALID = {"UN R94": "ece-r94", "UN R95": "ece-r95", "UN R34": "ece-r34"}

def test_prompt_lists_valid_targets_and_allows_none():
    reg = {"id": "us-fmvss-208", "title": "Occupant crash protection", "region": "US", "citation": "49 CFR 571.208", "body": "frontal..."}
    prompt = build_prompt(reg, VALID)
    assert "UN R94" in prompt
    assert "none" in prompt.lower() or "empty" in prompt.lower()

def test_parse_keeps_only_valid_corpus_numbers():
    out = parse_ai_equiv('{"un_equivalent_ai": ["UN R94", "UN R999"]}', VALID, grounded=[])
    assert out == ["UN R94"]

def test_parse_excludes_grounded_values():
    out = parse_ai_equiv('{"un_equivalent_ai": ["UN R94", "UN R95"]}', VALID, grounded=["UN R94"])
    assert out == ["UN R95"]

def test_parse_caps_at_two():
    out = parse_ai_equiv('{"un_equivalent_ai": ["UN R94","UN R95","UN R34"]}', VALID, grounded=[])
    assert len(out) == 2
