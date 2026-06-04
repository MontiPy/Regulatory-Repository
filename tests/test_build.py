"""Tests for scripts/build.py — markdown rendering, summarization, and validation."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build import (
    BuildIssue,
    as_list,
    load_region_series,
    render_markdown,
    report_line,
    stringify,
    summarize,
    validate_required,
    validate_un_equivalent,
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
