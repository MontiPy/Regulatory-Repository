"""Tests for scripts/auto_tag.py — open-tag parsing, prompt, and frontmatter write."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.auto_tag import OPEN_TAGS_CAP, parse_tags

TAXONOMY = {
    "commodities": ["Brakes", "Seats"],
    "systems": ["Braking"],
    "vehicle_categories": ["Passenger car"],
}


class TestParseOpenTags:
    def test_controlled_fields_still_filtered_to_taxonomy(self):
        text = '{"commodities": ["Brakes", "Nonsense"], "systems": [], "vehicle_categories": [], "open_tags": []}'
        result = parse_tags(text, TAXONOMY)
        assert result["commodities"] == ["Brakes"]

    def test_open_tags_passed_through_unfiltered(self):
        text = '{"commodities": [], "systems": [], "vehicle_categories": [], "open_tags": ["master cylinder", "brake booster"]}'
        result = parse_tags(text, TAXONOMY)
        assert result["open_tags"] == ["master cylinder", "brake booster"]

    def test_open_tags_deduped_case_insensitively(self):
        text = '{"open_tags": ["ISOFIX anchorage", "isofix anchorage", "ISOFIX Anchorage"]}'
        result = parse_tags(text, TAXONOMY)
        assert result["open_tags"] == ["ISOFIX anchorage"]

    def test_open_tags_capped(self):
        tags = [f"tag {i}" for i in range(OPEN_TAGS_CAP + 5)]
        import json
        text = json.dumps({"open_tags": tags})
        result = parse_tags(text, TAXONOMY)
        assert len(result["open_tags"]) == OPEN_TAGS_CAP

    def test_non_strings_and_blanks_dropped(self):
        text = '{"open_tags": ["valid", "", "   ", 5, null]}'
        result = parse_tags(text, TAXONOMY)
        assert result["open_tags"] == ["valid"]

    def test_invalid_json_returns_empty_open_tags(self):
        result = parse_tags("not json", TAXONOMY)
        assert result["open_tags"] == []

    def test_valid_but_non_object_json_returns_empty(self):
        # Valid JSON that isn't an object (null, list, bare string) must not
        # raise — it would otherwise abort the whole batch import.
        for text in ("null", "[1, 2, 3]", '"a string"'):
            result = parse_tags(text, TAXONOMY)
            assert result == {
                "commodities": [],
                "systems": [],
                "vehicle_categories": [],
                "open_tags": [],
            }


from scripts.auto_tag import MODEL, build_prompt, write_tags_to_file


class TestBuildPrompt:
    def test_prompt_requests_open_tags(self):
        reg = {"title": "T", "citation": "C", "region": "US", "body": "body"}
        prompt = build_prompt(reg, TAXONOMY)
        assert "open_tags" in prompt
        assert "at most 12" in prompt.lower()

    def test_model_is_sonnet(self):
        assert MODEL == "claude-sonnet-4-6"


class TestWriteTags:
    def test_open_tags_written_to_frontmatter(self, tmp_path):
        md = tmp_path / "rec.md"
        md.write_text("---\nid: rec\ntitle: T\n---\nbody\n", encoding="utf-8")
        write_tags_to_file(
            str(md),
            {"commodities": ["Brakes"], "systems": [], "vehicle_categories": [], "open_tags": ["master cylinder"]},
        )
        import frontmatter
        post = frontmatter.load(md)
        assert post["open_tags"] == ["master cylinder"]
        assert post["tagging_status"] == "llm-tagged"
