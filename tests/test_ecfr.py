"""Tests for connectors/ecfr.py — XML-to-Markdown conversion and slug/citation helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors.ecfr import (
    DEFAULT_TITLE,
    _make_citation,
    _make_slug,
    _parse_title_from_head,
    _xml_to_md,
)


class TestMakeSlug:
    def test_fmvss_section(self):
        assert _make_slug(49, 571, 108) == "us-fmvss-108"

    def test_fmvss_string_section(self):
        assert _make_slug(49, 571, "202a") == "us-fmvss-202a"

    def test_49cfr_part_only(self):
        assert _make_slug(49, 565, None) == "us-cfr-part-565"

    def test_49cfr_section(self):
        assert _make_slug(49, 575, 104) == "us-cfr575-104"

    def test_other_title_part_only(self):
        assert _make_slug(40, 86, None) == "us-40cfr-part-86"

    def test_other_title_with_section(self):
        assert _make_slug(47, 15, "209") == "us-47cfr15-209"


class TestMakeCitation:
    def test_with_section(self):
        assert _make_citation(49, 571, 108) == "49 CFR §571.108"

    def test_part_only(self):
        assert _make_citation(49, 565, None) == "49 CFR Part 565"

    def test_other_title_section(self):
        assert _make_citation(40, 86, "1811-27") == "40 CFR §86.1811-27"

    def test_other_title_part(self):
        assert _make_citation(47, 15, None) == "47 CFR Part 15"


class TestXmlToMd:
    def test_basic_conversion(self, ecfr_xml):
        result = _xml_to_md(ecfr_xml)
        assert "Lamps, reflective devices" in result
        assert "Each vehicle shall comply" in result

    def test_citation_italicized(self, ecfr_xml):
        result = _xml_to_md(ecfr_xml)
        assert "*" in result  # CITA becomes italic

    def test_invalid_xml_returns_truncated(self):
        result = _xml_to_md("not xml at all <<< >>>")
        assert isinstance(result, str)

    def test_no_triple_newlines(self, ecfr_xml):
        result = _xml_to_md(ecfr_xml)
        assert "\n\n\n" not in result

    def test_empty_xml(self):
        result = _xml_to_md("<DIV8></DIV8>")
        assert isinstance(result, str)


class TestParseTitleFromHead:
    def test_extracts_head(self, ecfr_xml):
        title = _parse_title_from_head(ecfr_xml)
        assert "Lamps, reflective devices" in title

    def test_missing_head_returns_empty(self):
        title = _parse_title_from_head("<DIV8><P>no head here</P></DIV8>")
        assert title == ""

    def test_invalid_xml_returns_empty(self):
        title = _parse_title_from_head("garbage")
        assert title == ""
