"""Tests for scripts/build.py — markdown rendering, summarization, and validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build import (
    BuildIssue,
    as_list,
    copy_static_assets,
    load_region_series,
    render_markdown,
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
        write_taxonomy_json({"regions": ["US"]}, {"US": {"series": "FMVSS", "name": "United States"}}, tmp_path)
        data = json.loads((tmp_path / "data" / "taxonomy.json").read_text(encoding="utf-8"))
        assert data["regions"] == ["US"]
        assert data["region_series"]["US"]["series"] == "FMVSS"

    def test_search_text_one_entry_each(self, tmp_path):
        write_search_text(self.RECORDS, tmp_path)
        data = json.loads((tmp_path / "data" / "search-text.json").read_text(encoding="utf-8"))
        assert data[0]["id"] == "a"
        assert "body a" in data[0]["text"]


class TestCopyAssets:
    @pytest.mark.xfail(reason="assets app.js and vendor land in later tasks")
    def test_copies_css_and_js(self, tmp_path):
        copy_static_assets(tmp_path)
        assert (tmp_path / "assets" / "styles.css").exists()
        assert (tmp_path / "assets" / "app.js").exists()
        assert (tmp_path / "assets" / "vendor" / "minisearch.min.js").exists()
