"""Tests for scripts/normalize_tags.py — collection, normalization, and writing."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.normalize_tags import (
    CHUNK_SIZE,
    _chunked,
    collect_open_tags,
    load_aliases,
    normalize,
    parse_grouping,
    write_aliases,
    write_vocabulary,
)


def _write_md(path: Path, open_tags: list[str]) -> None:
    body = "---\nid: " + path.stem + "\n"
    body += "open_tags:\n" + "".join(f"- {t}\n" for t in open_tags)
    body += "---\ncontent\n"
    path.write_text(body, encoding="utf-8")


class TestCollectOpenTags:
    def test_unique_and_sorted(self, tmp_path):
        _write_md(tmp_path / "a.md", ["Brake hose", "ISOFIX anchorage"])
        _write_md(tmp_path / "b.md", ["ISOFIX anchorage", "Wheel hub"])
        assert collect_open_tags(tmp_path) == ["Brake hose", "ISOFIX anchorage", "Wheel hub"]


class TestNormalize:
    def test_new_tags_grouped_existing_preserved(self):
        existing = {"old tag": "Old Canonical"}
        grouper = lambda tags: {t: "Brakes" for t in tags}  # noqa: E731
        result = normalize(["old tag", "brake", "brakes"], existing, grouper)
        assert result["old tag"] == "Old Canonical"   # untouched
        assert result["brake"] == "Brakes"
        assert result["brakes"] == "Brakes"

    def test_grouper_only_sees_new_tags(self):
        seen = {}
        def grouper(tags):
            seen["tags"] = list(tags)
            return {t: t for t in tags}
        normalize(["a", "b"], {"a": "A"}, grouper)
        assert seen["tags"] == ["b"]


class TestParseGrouping:
    def test_maps_each_tag(self):
        text = '{"brake": "Brakes", "brakes": "Brakes"}'
        assert parse_grouping(text, ["brake", "brakes"]) == {"brake": "Brakes", "brakes": "Brakes"}

    def test_missing_tag_falls_back_to_self(self):
        assert parse_grouping('{"brake": "Brakes"}', ["brake", "seat"])["seat"] == "seat"

    def test_invalid_json_falls_back_to_identity(self):
        assert parse_grouping("garbage", ["a", "b"]) == {"a": "a", "b": "b"}


class TestWrite:
    def test_aliases_round_trip(self, tmp_path):
        path = tmp_path / "tag_aliases.yaml"
        write_aliases(path, {"b": "B", "a": "A"})
        assert load_aliases(path) == {"a": "A", "b": "B"}

    def test_vocabulary_is_sorted_unique_canonicals(self, tmp_path):
        path = tmp_path / "discovered_vocabulary.yaml"
        write_vocabulary(path, {"x": "Brakes", "y": "Brakes", "z": "Seats"})
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == ["Brakes", "Seats"]

    def test_load_aliases_missing_file_is_empty(self, tmp_path):
        assert load_aliases(tmp_path / "nope.yaml") == {}

    def test_load_aliases_non_mapping_yaml_returns_empty(self, tmp_path):
        path = tmp_path / "list.yaml"
        path.write_text("- foo\n- bar\n", encoding="utf-8")
        assert load_aliases(path) == {}


class TestChunked:
    def test_exact_multiple(self):
        assert _chunked(["a", "b", "c", "d"], 2) == [["a", "b"], ["c", "d"]]

    def test_remainder(self):
        assert _chunked(["a", "b", "c"], 2) == [["a", "b"], ["c"]]

    def test_empty_list_returns_empty(self):
        assert _chunked([], 5) == []
