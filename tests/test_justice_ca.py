"""Tests for connectors/justice_ca.py — slug generation and XML section extraction."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors.justice_ca import _ca_slug, _citation, _extract_section, _reg_title_from_xml


class TestCaSlug:
    def test_simple_reg(self):
        result = _ca_slug("C.R.C.,_c._1038")
        assert result.startswith("ca-mvsr-")
        assert "1038" in result

    def test_with_section(self):
        result = _ca_slug("C.R.C.,_c._1038", "108")
        assert result.endswith("-s108")

    def test_decimal_section(self):
        result = _ca_slug("C.R.C.,_c._1038", "210.1")
        assert "210" in result

    def test_no_special_chars_in_slug(self):
        result = _ca_slug("C.R.C.,_c._1038", "108")
        import re
        assert re.match(r"^[a-z0-9-]+$", result)


class TestCitation:
    def test_without_section(self):
        assert _citation("C.R.C.,_c._1038") == "MVSR C.R.C.,_c._1038"

    def test_with_section(self):
        assert _citation("C.R.C.,_c._1038", "108") == "MVSR C.R.C.,_c._1038 s. 108"


class TestRegTitleFromXml:
    def test_long_title(self, ca_xml):
        root = ET.fromstring(ca_xml)
        title = _reg_title_from_xml(root)
        assert title == "Motor Vehicle Safety Regulations"

    def test_missing_title_returns_empty(self):
        root = ET.fromstring("<Regulations><Section/></Regulations>")
        title = _reg_title_from_xml(root)
        assert title == ""


class TestExtractSection:
    def test_finds_existing_section(self, ca_xml):
        root = ET.fromstring(ca_xml)
        title, md = _extract_section(root, "108")
        assert "108" in title
        assert md  # non-empty

    def test_missing_section_returns_empty_body(self, ca_xml):
        root = ET.fromstring(ca_xml)
        title, md = _extract_section(root, "999")
        assert "999" in title
        assert md == ""

    def test_title_includes_heading(self, ca_xml):
        root = ET.fromstring(ca_xml)
        title, _ = _extract_section(root, "108")
        assert "Lighting" in title
