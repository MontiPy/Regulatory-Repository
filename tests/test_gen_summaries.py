"""Tests for scripts/gen_summaries.py — selection, parsing, frontmatter write."""
from __future__ import annotations

import sys
from pathlib import Path

import frontmatter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.gen_summaries import (
    parse_summary,
    should_process,
    write_summary_to_file,
)


class TestShouldProcess:
    def test_default_skips_when_summary_present(self):
        meta = {"summary": "x", "summary_hash": "abc"}
        assert should_process(meta, "abc", regen=False, stale_only=False) is False

    def test_default_includes_when_no_summary(self):
        assert should_process({}, "abc", regen=False, stale_only=False) is True

    def test_regen_includes_everything(self):
        meta = {"summary": "x", "summary_hash": "abc"}
        assert should_process(meta, "abc", regen=True, stale_only=False) is True

    def test_stale_only_includes_when_hash_mismatch(self):
        meta = {"summary": "x", "summary_hash": "old"}
        assert should_process(meta, "new", regen=False, stale_only=True) is True

    def test_stale_only_skips_when_hash_matches(self):
        meta = {"summary": "x", "summary_hash": "same"}
        assert should_process(meta, "same", regen=False, stale_only=True) is False

    def test_stale_only_skips_when_no_summary(self):
        assert should_process({}, "new", regen=False, stale_only=True) is False


class TestParseSummary:
    def test_strips_code_fences(self):
        assert parse_summary("```\nHello world.\n```") == "Hello world."

    def test_collapses_whitespace(self):
        assert parse_summary("Hello   \n  world.") == "Hello world."

    def test_strips_wrapping_quotes(self):
        assert parse_summary('"Hello world."') == "Hello world."

    def test_strips_smart_quote_wrapping(self):
        assert parse_summary('“Hello world.”') == "Hello world."

    def test_truncates_overlong_text(self):
        long = "word " * 100
        result = parse_summary(long)
        assert len(result) <= 323  # cap + ellipsis
        assert result.endswith("...")


class TestWriteSummaryToFile:
    def test_writes_three_fields(self, tmp_path):
        path = tmp_path / "reg.md"
        post = frontmatter.Post("Body text", id="reg", title="T")
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

        write_summary_to_file(str(path), "A short summary.", "hash123")

        reloaded = frontmatter.load(path)
        assert reloaded["summary"] == "A short summary."
        assert reloaded["summary_hash"] == "hash123"
        assert reloaded["summary_generated_at"]  # timestamp set
        assert reloaded.content.strip() == "Body text"  # body untouched
