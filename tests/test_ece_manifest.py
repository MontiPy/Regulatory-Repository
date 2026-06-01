from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_ece_manifest_includes_external_projections() -> None:
    manifest = yaml.safe_load((ROOT / "manifests" / "ece.yaml").read_text(encoding="utf-8"))
    records = manifest["records"]
    titles_by_regulation = {str(record["regulation"]): record["title"] for record in records}

    assert titles_by_regulation["26"] == "External Projections"


def test_ece_manifest_includes_workbook_gap_regulations() -> None:
    manifest = yaml.safe_load((ROOT / "manifests" / "ece.yaml").read_text(encoding="utf-8"))
    records = manifest["records"]
    titles_by_regulation = {str(record["regulation"]): record["title"] for record in records}

    for regulation in ("0", "28", "37", "39", "45", "55", "144", "163"):
        assert regulation in titles_by_regulation

    assert "Real Driving Emissions" in titles_by_regulation["168"]
