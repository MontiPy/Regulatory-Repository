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
