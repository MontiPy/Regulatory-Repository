"""Tests for connectors/egov_jp.py — article number matching and XML extraction."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors.egov_jp import _article_matches, _law_xml_to_article


class TestArticleMatches:
    # Integer articles
    def test_exact_integer(self):
        assert _article_matches("22", "22") is True

    def test_different_integers(self):
        assert _article_matches("22", "23") is False

    # Sub-articles — underscore in XML, hyphen in manifest
    def test_underscore_vs_hyphen(self):
        assert _article_matches("11_2", "11-2") is True

    def test_hyphen_vs_underscore(self):
        assert _article_matches("11-2", "11_2") is True

    # Exact match fallback
    def test_exact_string_match(self):
        assert _article_matches("22_3", "22_3") is True

    def test_hyphen_exact(self):
        assert _article_matches("13-H", "13-H") is True

    # No match
    def test_different_sub_article(self):
        assert _article_matches("11_2", "11_3") is False

    def test_integer_vs_sub_article(self):
        assert _article_matches("11", "11_2") is False


class TestLawXmlToArticle:
    def test_extracts_simple_article(self, egov_xml):
        title, body = _law_xml_to_article(egov_xml, "11")
        assert "11" in title
        assert body  # non-empty markdown

    def test_sub_article_underscore(self, egov_xml):
        title, body = _law_xml_to_article(egov_xml, "11_2")
        assert body  # should find Article Num="11_2"

    def test_sub_article_hyphen_notation(self, egov_xml):
        # manifest uses "11-2", XML uses "11_2" — should still match
        title, body = _law_xml_to_article(egov_xml, "11-2")
        assert body

    def test_article_with_caption(self, egov_xml):
        title, body = _law_xml_to_article(egov_xml, "11")
        assert "後写鏡" in title or "11" in title

    def test_missing_article_returns_empty(self, egov_xml):
        title, body = _law_xml_to_article(egov_xml, "999")
        assert title == ""
        assert body == ""

    def test_invalid_xml_returns_empty(self):
        title, body = _law_xml_to_article("not xml", "11")
        assert title == ""
        assert body == ""
