from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_spreadsheet_manifest() -> dict:
    manifest_path = ROOT / "manifests" / "spreadsheet.yaml"
    assert manifest_path.exists()
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8"))


def test_spreadsheet_manifest_covers_representative_workbook_gap_rows() -> None:
    manifest = _load_spreadsheet_manifest()
    records = {record["workbook_id"]: record for record in manifest["records"]}

    expected = {
        "REG-0370": (
            "au-workbook-reg-0370-road-vehicle-standards-act-2018-road-vehicle-"
            "standards-rules-2019"
        ),
        "REG-0610": "mx-workbook-reg-0610-nom-194-se-2021",
        "REG-0623": "za-workbook-reg-0623-vc-8056",
        "REG-0643": "other-workbook-reg-0643-iso-26262",
    }

    for workbook_id, record_id in expected.items():
        assert records[workbook_id]["id"] == record_id


def test_spreadsheet_manifest_records_have_markdown_files() -> None:
    manifest = _load_spreadsheet_manifest()

    missing = [
        record["id"]
        for record in manifest["records"]
        if not (ROOT / "regulations" / f"{record['id']}.md").exists()
    ]

    assert missing == []
