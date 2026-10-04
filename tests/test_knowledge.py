"""Tests for scripts/knowledge.py — the curated markets / crosswalk / glossary layer."""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import knowledge  # noqa: E402
from scripts._fsutil import list_md_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _corpus_ids() -> set[str]:
    return {p.stem for p in list_md_files(ROOT / "regulations")}


def _regions() -> set[str]:
    raw = yaml.safe_load((ROOT / "taxonomy.yaml").read_text(encoding="utf-8"))
    return set(raw["regions"])


# ── The real, checked-in knowledge data ────────────────────────────────────

@pytest.fixture(scope="module")
def real():
    payload, errors = knowledge.build_knowledge(_corpus_ids(), _regions())
    return payload, errors


def test_real_knowledge_has_no_errors(real):
    _payload, errors = real
    assert errors == []


def test_every_corpus_region_has_a_market_profile(real):
    payload, _ = real
    covered = {r for m in payload["markets"]["markets"] for r in m["regions"]}
    # OTHER holds cross-cutting standards (ISO, IATF…), not a market.
    assert _regions() - {"OTHER"} <= covered


def test_market_codes_unique_and_groups_valid(real):
    payload, _ = real
    markets = payload["markets"]["markets"]
    codes = [m["code"] for m in markets]
    assert len(codes) == len(set(codes))
    assert all(m["group"] in knowledge.GROUPS for m in markets)


def test_markets_cover_every_world_region(real):
    payload, _ = real
    groups = {m["group"] for m in payload["markets"]["markets"]}
    assert groups == set(knowledge.GROUPS)


def test_crosswalk_columns_point_at_markets(real):
    payload, _ = real
    codes = {m["code"] for m in payload["markets"]["markets"]}
    assert all(c["market"] in codes for c in payload["crosswalk"]["columns"])


def test_crosswalk_powertrains_expanded(real):
    payload, _ = real
    for topic in payload["crosswalk"]["topics"]:
        assert topic["powertrains"], topic["id"]
        assert set(topic["powertrains"]) <= set(knowledge.POWERTRAINS)
    avas = next(t for t in payload["crosswalk"]["topics"] if t["id"] == "avas")
    assert "ICE" not in avas["powertrains"]
    frontal = next(t for t in payload["crosswalk"]["topics"] if t["id"] == "frontal-full")
    assert frontal["powertrains"] == knowledge.POWERTRAINS


def test_crosswalk_cells_default_to_mandatory(real):
    payload, _ = real
    for topic in payload["crosswalk"]["topics"]:
        for cell in topic["cells"].values():
            assert cell["status"] in knowledge.CELL_STATUSES


def test_regime_labels_attached(real):
    payload, _ = real
    us = next(m for m in payload["markets"]["markets"] if m["code"] == "US")
    assert us["regime"] == "self-certification"
    assert us["regime_label"] == "Self-certification"


# ── Validation behaviour on synthetic data ─────────────────────────────────

GOOD_MARKET = {
    "code": "XX", "name": "Testland", "group": "Europe", "regions": ["EU"], "drive": "LHD",
    "regime": "type-approval", "basis": "UN R", "un_1958": True, "un_1998": None,
    "authorities": [{"name": "Agency", "scope": "all", "url": "https://example.org"}],
    "accepts": [], "marks": [], "emissions": "Euro 6", "language": "Test",
    "process": ["Apply"], "records": ["rec-a"], "confidence": "low",
}


@pytest.fixture
def kdir(tmp_path, monkeypatch):
    markets = tmp_path / "markets"
    markets.mkdir()
    monkeypatch.setattr(knowledge, "MARKETS_DIR", markets)
    monkeypatch.setattr(knowledge, "CROSSWALK_PATH", tmp_path / "crosswalk.yaml")
    monkeypatch.setattr(knowledge, "GLOSSARY_PATH", tmp_path / "glossary.yaml")
    (tmp_path / "crosswalk.yaml").write_text(yaml.safe_dump({
        "columns": [{"key": "XX", "label": "Testland", "short": "XX", "market": "XX"}],
        "groups": ["G"],
        "topics": [{"id": "t1", "group": "G", "title": "T", "description": "d",
                    "powertrains": ["all"], "cells": {"XX": {"cite": "Reg 1", "records": ["rec-a"]}}}],
    }), encoding="utf-8")
    (tmp_path / "glossary.yaml").write_text(yaml.safe_dump([
        {"term": "CoP", "definition": "Conformity of production", "markets": ["XX"]},
    ]), encoding="utf-8")
    return tmp_path


def _write_markets(kdir: Path, markets: list[dict]) -> None:
    (kdir / "markets" / "m.yaml").write_text(yaml.safe_dump(markets), encoding="utf-8")


def _run(ids=frozenset({"rec-a"}), regions=frozenset({"EU"})):
    return knowledge.build_knowledge(set(ids), set(regions))


def test_valid_synthetic_data_passes(kdir):
    _write_markets(kdir, [GOOD_MARKET])
    payload, errors = _run()
    assert errors == []
    assert payload["crosswalk"]["topics"][0]["cells"]["XX"]["status"] == "mandatory"


def test_unknown_record_id_is_an_error_and_dropped(kdir):
    _write_markets(kdir, [dict(GOOD_MARKET, records=["rec-a", "rec-missing"])])
    payload, errors = _run()
    assert any("unknown record id 'rec-missing'" in e for e in errors)
    assert payload["markets"]["markets"][0]["records"] == ["rec-a"]


def test_crosswalk_unknown_record_is_an_error(kdir):
    _write_markets(kdir, [GOOD_MARKET])
    _payload, errors = _run(ids=frozenset())
    assert any("crosswalk:t1.XX: unknown record id 'rec-a'" in e for e in errors)


@pytest.mark.parametrize("field,value,fragment", [
    ("regime", "vibes", "regime 'vibes'"),
    ("drive", "center", "drive 'center'"),
    ("confidence", "certain", "confidence 'certain'"),
    ("group", "Atlantis", "group 'Atlantis'"),
    ("un_1958", "yes", "un_1958 must be true, false or null"),
    ("regions", ["ZZ"], "region 'ZZ' not in taxonomy"),
])
def test_bad_enum_values_are_errors(kdir, field, value, fragment):
    _write_markets(kdir, [dict(GOOD_MARKET, **{field: value})])
    _payload, errors = _run()
    assert any(fragment in e for e in errors), errors


def test_missing_and_unknown_keys(kdir):
    bad = {k: v for k, v in GOOD_MARKET.items() if k != "basis"}
    bad["surprise"] = 1
    _write_markets(kdir, [bad])
    _payload, errors = _run()
    assert any("missing keys ['basis']" in e for e in errors)
    assert any("unknown keys ['surprise']" in e for e in errors)


def test_duplicate_market_code(kdir):
    _write_markets(kdir, [GOOD_MARKET, GOOD_MARKET])
    _payload, errors = _run()
    assert any("duplicate market code" in e for e in errors)


def test_authority_with_unquoted_comma_is_caught(kdir):
    # `{ name: A, B (C), scope: x }` parses into a stray key — the classic YAML trap.
    (kdir / "markets" / "m.yaml").write_text(textwrap.dedent("""\
        - code: XX
          name: Testland
          group: Europe
          regions: [EU]
          drive: LHD
          regime: type-approval
          basis: UN R
          un_1958: true
          un_1998: null
          authorities:
            - { name: Ministry of Trade, Industry (MTI), scope: all, url: "https://example.org" }
          accepts: []
          marks: []
          emissions: Euro 6
          language: Test
          process: [Apply]
          records: []
          confidence: low
        """), encoding="utf-8")
    _payload, errors = _run()
    assert any("authority entries need name" in e for e in errors)


def test_authority_url_must_be_http(kdir):
    _write_markets(kdir, [dict(GOOD_MARKET, authorities=[{"name": "A", "url": "javascript:alert(1)"}])])
    _payload, errors = _run()
    assert any("authority url must be http(s)" in e for e in errors)


def test_crosswalk_cell_validation(kdir):
    _write_markets(kdir, [GOOD_MARKET])
    data = yaml.safe_load((kdir / "crosswalk.yaml").read_text(encoding="utf-8"))
    data["topics"][0]["cells"] = {
        "XX": {"cite": "", "records": []},
        "YY": {"cite": "Other"},
    }
    data["topics"].append(dict(data["topics"][0], id="t2", powertrains=["Diesel"], cells={"XX": {"cite": "c", "status": "maybe"}}))
    data["topics"].append(dict(data["topics"][0], id="t1", cells={}))
    (kdir / "crosswalk.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    _payload, errors = _run()
    joined = "\n".join(errors)
    assert "crosswalk:t1.XX: cell needs a non-empty cite" in joined
    assert "crosswalk:t1.YY: unknown column" in joined
    assert "powertrain 'Diesel'" in joined
    assert "status 'maybe'" in joined
    assert "crosswalk:t1: duplicate topic id" in joined


def test_crosswalk_column_must_reference_market(kdir):
    _write_markets(kdir, [GOOD_MARKET])
    data = yaml.safe_load((kdir / "crosswalk.yaml").read_text(encoding="utf-8"))
    data["columns"].append({"key": "ZZ", "label": "Z", "short": "Z", "market": "NOPE"})
    (kdir / "crosswalk.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    _payload, errors = _run()
    assert any("column ZZ references unknown market 'NOPE'" in e for e in errors)


def test_glossary_unknown_market(kdir):
    _write_markets(kdir, [GOOD_MARKET])
    (kdir / "glossary.yaml").write_text(yaml.safe_dump([
        {"term": "X", "definition": "d", "markets": ["NOPE"]},
    ]), encoding="utf-8")
    _payload, errors = _run()
    assert any("glossary:X: unknown market code 'NOPE'" in e for e in errors)


def test_build_writes_knowledge_json(tmp_path):
    import json

    from scripts.build import write_knowledge_json

    write_knowledge_json({"markets": {"m": 1}, "crosswalk": {"c": 2}, "glossary": [3]}, tmp_path)
    data = tmp_path / "data"
    assert json.loads((data / "markets.json").read_text(encoding="utf-8")) == {"m": 1}
    assert json.loads((data / "crosswalk.json").read_text(encoding="utf-8")) == {"c": 2}
    assert json.loads((data / "glossary.json").read_text(encoding="utf-8")) == [3]
