"""Tests for scripts/build.py — markdown rendering, summarization, and validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build import (
    BuildIssue,
    _body_hash,
    as_list,
    build_record,
    clean_body,
    clean_summary_display_text,
    copy_static_assets,
    load_region_series,
    render_markdown,
    render_shell,
    report_line,
    search_text_for,
    split_record,
    stringify,
    summarize,
    validate_required,
    validate_un_equivalent,
    write_index_json,
    write_record_bodies,
    write_taxonomy_json,
    write_search_text,
)


class TestStringify:
    def test_none_returns_empty(self):
        assert stringify(None) == ""

    def test_int_converts(self):
        assert stringify(42) == "42"

    def test_str_passthrough(self):
        assert stringify("hello") == "hello"


class TestAsList:
    def test_none_returns_empty(self):
        issues: list[BuildIssue] = []
        assert as_list(None, "field", issues) == []
        assert not issues

    def test_list_returned_as_is(self):
        issues: list[BuildIssue] = []
        assert as_list(["a", "b"], "field", issues) == ["a", "b"]

    def test_non_list_adds_error(self):
        issues: list[BuildIssue] = []
        as_list("not a list", "field", issues)
        assert len(issues) == 1
        assert issues[0].severity == "ERROR"


class TestRenderMarkdown:
    def test_basic_heading(self):
        html = render_markdown("# Hello\n\nworld")
        assert "<h1>" in html
        assert "Hello" in html

    def test_bold_text(self):
        html = render_markdown("**bold**")
        assert "<strong>" in html

    def test_strips_script_tags(self):
        html = render_markdown("text\n\n<script>alert(1)</script>")
        assert "<script>" not in html

    def test_table_rendered(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = render_markdown(md)
        assert "<table>" in html


class TestSummarize:
    def test_short_text_unchanged(self):
        html = "<p>Short text.</p>"
        result = summarize(html)
        assert result == "Short text."

    def test_long_text_truncated(self):
        html = "<p>" + "word " * 100 + "</p>"
        result = summarize(html)
        assert len(result) <= 260
        assert result.endswith("...")

    def test_strips_tags(self):
        html = "<h1>Title</h1><p>Body text here.</p>"
        result = summarize(html)
        assert "<h1>" not in result
        assert "Title" in result

    def test_html_entities_unescaped(self):
        html = "<p>Section &sect; 108</p>"
        result = summarize(html)
        assert "§" in result


class TestCleanSummaryDisplayText:
    def test_removes_metadata_scaffold_after_useful_title(self):
        raw = (
            "Argentina model configuration and environmental configuration licenses "
            "Regulated Area: Market access / type approval / emissions "
            "Applicability: Applies to new vehicles for public-road circulation in Argentina"
        )
        assert clean_summary_display_text(raw) == (
            "Argentina model configuration and environmental configuration licenses"
        )

    def test_keeps_short_plain_summary(self):
        assert clean_summary_display_text("Brake systems for passenger cars") == (
            "Brake systems for passenger cars"
        )

    def test_removes_scaffold_after_short_real_title(self):
        # Real corpus titles can be short (~28 chars); they must still be
        # cleaned, so the floor sits below typical title length.
        raw = (
            "Driver Forward Field of View Regulated Area: Visibility / lighting "
            "Applicability: Mirrors, cameras, glazing"
        )
        assert clean_summary_display_text(raw) == "Driver Forward Field of View"

    def test_preserves_real_body_with_source_label(self):
        # DELTA-1: "Source:"/"Notes:" occur in real legal bodies and must NOT
        # trigger truncation — only the workbook scaffolding labels do.
        raw = (
            "This standard specifies requirements for occupant crash protection "
            "to reduce deaths and injuries. Source: 49 FR 12345. Compliance is "
            "required for vehicles manufactured on or after September 1, 2026."
        )
        assert clean_summary_display_text(raw) == raw


class TestValidateRequired:
    REQUIRED = {
        "id": "test-id",
        "title": "Test",
        "region": "US",
        "citation": "49 CFR §571.108",
        "status": "in-force",
        "source_url": "https://example.com",
        "source_api": "ecfr",
        "last_pulled": "2024-01-01T00:00:00+00:00",
        "tagging_status": "untagged",
    }

    def test_valid_record_no_issues(self, tmp_path):
        path = tmp_path / "test-id.md"
        issues: list[BuildIssue] = []
        validate_required(dict(self.REQUIRED), path, issues)
        assert not issues

    def test_missing_field_adds_error(self, tmp_path):
        path = tmp_path / "test-id.md"
        meta = {k: v for k, v in self.REQUIRED.items() if k != "title"}
        issues: list[BuildIssue] = []
        validate_required(meta, path, issues)
        assert any("title" in str(i) for i in issues)

    def test_id_mismatch_adds_error(self, tmp_path):
        path = tmp_path / "different-id.md"
        issues: list[BuildIssue] = []
        validate_required(dict(self.REQUIRED), path, issues)
        assert any("id" in str(i).lower() for i in issues)

    def test_unknown_key_adds_error(self, tmp_path):
        path = tmp_path / "test-id.md"
        meta = dict(self.REQUIRED)
        meta["unknown_field"] = "value"
        issues: list[BuildIssue] = []
        validate_required(meta, path, issues)
        assert any("unknown" in str(i) for i in issues)


class TestValidateUnEquivalent:
    def test_valid_un_r_number(self):
        issues: list[BuildIssue] = []
        validate_un_equivalent({"un_equivalent": ["UN R48", "UN R100"]}, issues)
        assert not issues

    def test_invalid_format_adds_error(self):
        issues: list[BuildIssue] = []
        validate_un_equivalent({"un_equivalent": ["UNECE R48"]}, issues)
        assert issues

    def test_empty_list_ok(self):
        issues: list[BuildIssue] = []
        validate_un_equivalent({"un_equivalent": []}, issues)
        assert not issues

    def test_suffix_letter_ok(self):
        issues: list[BuildIssue] = []
        validate_un_equivalent({"un_equivalent": ["UN R13a"]}, issues)
        assert not issues


class TestReportLine:
    def test_ok_no_issues(self):
        record = {"id": "test-id"}
        line = report_line(record, [])
        assert line.startswith("OK")

    def test_error_severity(self):
        record = {"id": "test-id"}
        issues = [BuildIssue("ERROR", "something wrong")]
        line = report_line(record, issues)
        assert line.startswith("ERROR")

    def test_warn_severity(self):
        record = {"id": "test-id"}
        issues = [BuildIssue("WARN", "minor issue")]
        line = report_line(record, issues)
        assert line.startswith("WARN")

    def test_missing_id_placeholder(self):
        line = report_line({}, [])
        assert "(missing id)" in line


class TestLoadRegionSeries:
    def test_known_region_has_series_and_name(self):
        mapping = load_region_series()
        assert mapping["US"]["series"] == "FMVSS"
        assert mapping["US"]["name"] == "United States"

    def test_all_values_have_series_and_name_keys(self):
        mapping = load_region_series()
        for region, entry in mapping.items():
            assert set(entry) == {"series", "name"}, region


class TestSplitRecord:
    FULL = {
        "id": "us-fmvss-208", "title": "Occupant crash protection",
        "region": "US", "citation": "49 CFR §571.208", "status": "in-force",
        "source_url": "https://example.com", "source_api": "ecfr",
        "last_pulled": "2026-01-01T00:00:00+00:00", "tagging_status": "llm-tagged",
        "tagged_at": "", "aliases": [], "commodities": ["Airbags"],
        "systems": ["Crashworthiness"], "vehicle_categories": ["Passenger car"],
        "un_equivalent": [], "related": [], "tags": [], "paywall": False,
        "translation_status": "", "summary_text": "A summary.",
        "body_html": "<p>Long body…</p>",
    }

    def test_light_omits_body(self):
        light, body = split_record(self.FULL)
        assert "body_html" not in light
        assert body == "<p>Long body…</p>"

    def test_light_keeps_summary_and_tags(self):
        light, _ = split_record(self.FULL)
        assert light["summary_text"] == "A summary."
        assert light["commodities"] == ["Airbags"]

    def test_body_defaults_empty(self):
        full = dict(self.FULL); del full["body_html"]
        _, body = split_record(full)
        assert body == ""


class TestSearchTextFor:
    def test_includes_title_and_body_plain(self):
        rec = {"id": "x", "title": "Brakes", "citation": "C1", "aliases": [],
               "tags": [], "commodities": ["Brakes"], "systems": ["Braking"],
               "vehicle_categories": [], "summary_text": "sum",
               "body_html": "<p>Hydraulic <strong>brake</strong> lines.</p>"}
        blob = search_text_for(rec)
        assert blob["id"] == "x"
        assert "Brakes" in blob["text"]
        assert "Hydraulic brake lines." in blob["text"]
        assert "<strong>" not in blob["text"]

    def test_body_capped(self):
        rec = {"id": "y", "title": "", "citation": "", "aliases": [], "tags": [],
               "commodities": [], "systems": [], "vehicle_categories": [],
               "summary_text": "", "body_html": "<p>" + "x" * 50000 + "</p>"}
        blob = search_text_for(rec)
        assert len(blob["text"]) <= 20100  # 20k body cap + small header fields


class TestBundleWriters:
    RECORDS = [
        {"id": "a", "title": "A", "region": "US", "citation": "c", "status": "in-force",
         "source_url": "", "source_api": "ecfr", "last_pulled": "", "tagging_status": "untagged",
         "tagged_at": "", "aliases": [], "commodities": [], "systems": [],
         "vehicle_categories": [], "un_equivalent": [], "related": [], "tags": [],
         "paywall": False, "translation_status": "", "summary_text": "sa",
         "body_html": "<p>body a</p>"},
    ]

    def test_index_json_has_no_bodies(self, tmp_path):
        write_index_json(self.RECORDS, tmp_path)
        data = json.loads((tmp_path / "data" / "index.json").read_text(encoding="utf-8"))
        assert data[0]["id"] == "a"
        assert "body_html" not in data[0]
        assert data[0]["summary_text"] == "sa"

    def test_record_bodies_one_file_each(self, tmp_path):
        write_record_bodies(self.RECORDS, tmp_path)
        body = json.loads((tmp_path / "data" / "records" / "a.json").read_text(encoding="utf-8"))
        assert body["id"] == "a"
        assert body["body_html"] == "<p>body a</p>"

    def test_taxonomy_json_includes_region_series(self, tmp_path):
        write_taxonomy_json({"regions": ["US"]}, {"US": {"series": "FMVSS", "name": "United States"}}, {}, tmp_path)
        data = json.loads((tmp_path / "data" / "taxonomy.json").read_text(encoding="utf-8"))
        assert data["regions"] == ["US"]
        assert data["region_series"]["US"]["series"] == "FMVSS"

    def test_search_text_one_entry_each(self, tmp_path):
        write_search_text(self.RECORDS, tmp_path)
        data = json.loads((tmp_path / "data" / "search-text.json").read_text(encoding="utf-8"))
        assert data[0]["id"] == "a"
        assert "body a" in data[0]["text"]


class TestCopyAssets:
    def test_copies_css_and_js(self, tmp_path):
        copy_static_assets(tmp_path)
        assert (tmp_path / "assets" / "styles.css").exists()
        assert (tmp_path / "assets" / "app.js").exists()
        assert (tmp_path / "assets" / "vendor" / "minisearch.min.js").exists()

    def test_idempotent_on_existing_dest(self, tmp_path):
        copy_static_assets(tmp_path)
        copy_static_assets(tmp_path)  # must not raise on pre-existing dest
        assert (tmp_path / "assets" / "styles.css").exists()
        assert (tmp_path / "assets" / "app.js").exists()
        assert (tmp_path / "assets" / "vendor" / "minisearch.min.js").exists()


class TestRenderShell:
    def test_shell_has_no_embedded_records(self, tmp_path):
        meta = {"timestamp": "t", "count": 1, "region_counts": {"US": 1}, "tagging_status_counts": {}}
        render_shell(meta, tmp_path)
        html = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "records_json" not in html
        assert 'src="assets/app.js"' in html
        assert 'href="assets/styles.css"' in html
        assert "1 regulations" in html


class TestBuildBundleIntegration:
    def test_emits_full_bundle(self, tmp_path, monkeypatch):
        from scripts import build as build_mod
        monkeypatch.setattr(build_mod, "REGULATIONS_DIR", Path(__file__).parent / "fixtures" / "regs")
        monkeypatch.setattr(build_mod, "DIST_DIR", tmp_path / "dist")
        rc = build_mod.build(draft=True)
        dist = tmp_path / "dist"
        assert (dist / "index.html").exists()
        assert (dist / "assets" / "app.js").exists()
        index = json.loads((dist / "data" / "index.json").read_text(encoding="utf-8"))
        ids = {r["id"] for r in index}
        assert ids == {"us-fmvss-208", "eu-sample"}
        assert all("body_html" not in r for r in index)
        assert (dist / "data" / "records" / "us-fmvss-208.json").exists()
        assert (dist / "data" / "taxonomy.json").exists()
        search = json.loads((dist / "data" / "search-text.json").read_text(encoding="utf-8"))
        assert any("brake" in s["text"].lower() for s in search)
        assert rc in (0, 1)


from scripts.build import derive_related, build_un_index


def test_build_un_index_maps_un_number_to_ece_id():
    records = [
        {"id": "ece-r94", "un_equivalent": [], "un_equivalent_ai": []},
        {"id": "ece-r13-h", "un_equivalent": [], "un_equivalent_ai": []},
        {"id": "us-fmvss-208", "un_equivalent": [], "un_equivalent_ai": ["UN R94"]},
    ]
    assert build_un_index(records) == {"UN R94": "ece-r94", "UN R13H": "ece-r13-h"}


def test_derive_related_links_grounded_siblings_and_ece_record():
    records = [
        {"id": "ece-r94", "un_equivalent": [], "un_equivalent_ai": []},
        {"id": "us-fmvss-208", "un_equivalent": ["UN R94"], "un_equivalent_ai": []},
        {"id": "ca-cmvss-208", "un_equivalent": ["UN R94"], "un_equivalent_ai": []},
        {"id": "us-fmvss-101", "un_equivalent": [], "un_equivalent_ai": ["UN R94"]},
    ]
    related = derive_related(records)
    assert set(related["us-fmvss-208"]) == {"ece-r94", "ca-cmvss-208"}
    assert set(related["ece-r94"]) == {"us-fmvss-208", "ca-cmvss-208"}
    assert related["us-fmvss-101"] == []


def test_derive_related_caps_fan_out_at_12():
    records = [{"id": "ece-r10", "un_equivalent": [], "un_equivalent_ai": []}]
    records += [{"id": f"reg-{i}", "un_equivalent": ["UN R10"], "un_equivalent_ai": []} for i in range(20)]
    related = derive_related(records)
    assert len(related["ece-r10"]) == 12


def test_un_equivalent_ai_validates_format():
    from scripts.build import validate_un_equivalent_ai, BuildIssue
    issues = []
    validate_un_equivalent_ai({"un_equivalent_ai": ["UN R94", "bogus"]}, issues)
    assert any("bogus" in i.message for i in issues)


class TestOpenTagsInBuild:
    def test_search_text_includes_open_tags(self):
        record = {
            "id": "r1",
            "title": "T",
            "open_tags": ["master cylinder", "brake booster"],
        }
        blob = search_text_for(record)
        assert "master cylinder" in blob["text"]
        assert "brake booster" in blob["text"]

    def test_open_tags_is_an_accepted_frontmatter_key(self):
        from scripts.build import ALLOWED_KEYS, LIST_FIELDS
        assert "open_tags" in ALLOWED_KEYS
        assert "open_tags" in LIST_FIELDS


import frontmatter


class TestBuildRecordSummary:
    BODY = "# Reversing Lamps\n\nThis Standard specifies requirements for reversing lamps fitted to vehicles.\n"

    def _write_reg(self, path, body, **extra):
        meta = {
            "id": path.stem,
            "title": "Test Reg",
            "region": "US",
            "citation": "49 CFR 571.108",
            "status": "in-force",
            "source_url": "https://example.com",
            "source_api": "ecfr",
            "last_pulled": "2024-01-01T00:00:00+00:00",
            "tagging_status": "untagged",
        }
        meta.update(extra)
        post = frontmatter.Post(body, **meta)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def _current_hash(self, body):
        return _body_hash(clean_body(body, "ecfr"))

    def test_no_summary_falls_back_to_heuristic(self, tmp_path):
        path = tmp_path / "test-id.md"
        self._write_reg(path, self.BODY)
        record, _issues = build_record(path, {}, draft=True)
        assert record["summary_ai"] is False
        assert record["summary_stale"] is False
        assert record["summary_text"]  # non-empty heuristic excerpt
        assert "AI summary" not in record["summary_text"]

    def test_summary_present_is_surfaced_and_flagged_ai(self, tmp_path):
        path = tmp_path / "test-id.md"
        self._write_reg(
            path, self.BODY,
            summary="Sets requirements for reversing lamps on vehicles.",
            summary_hash=self._current_hash(self.BODY),
        )
        record, _issues = build_record(path, {}, draft=True)
        assert record["summary_text"] == "Sets requirements for reversing lamps on vehicles."
        assert record["summary_ai"] is True
        assert record["summary_stale"] is False

    def test_summary_with_mismatched_hash_is_stale(self, tmp_path):
        path = tmp_path / "test-id.md"
        self._write_reg(
            path, self.BODY,
            summary="Sets requirements for reversing lamps on vehicles.",
            summary_hash="deadbeef",  # does not match current body
        )
        record, _issues = build_record(path, {}, draft=True)
        assert record["summary_ai"] is True
        assert record["summary_stale"] is True
