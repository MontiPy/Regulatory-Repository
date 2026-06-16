"""Tests for scripts/_fsutil.py — OneDrive-safe file listing."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._fsutil import list_md_files


class TestListMdFiles:
    def test_finds_md_files_sorted(self, tmp_path):
        (tmp_path / "b.md").write_text("", encoding="utf-8")
        (tmp_path / "a.md").write_text("", encoding="utf-8")
        (tmp_path / "c.txt").write_text("", encoding="utf-8")
        result = list_md_files(tmp_path)
        assert result == [tmp_path / "a.md", tmp_path / "b.md"]

    def test_empty_dir_returns_empty(self, tmp_path):
        assert list_md_files(tmp_path) == []
