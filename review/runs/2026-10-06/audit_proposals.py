"""Root audit: require exact adjudicated values and no additional semantic edits."""
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "review"))
import apply_patches

decisions = json.loads((RUN / "adjudication.json").read_text())
expected_records = {}
for d in decisions:
    if d["disposition"] == "apply" and d["kind"] == "records":
        expected_records.setdefault(d["id"], {}).update({d["patch_field"]: d["patch_value"], **d["additional_fields"]})
paths = [ROOT / "review/patches" / f"r20261006-group-{i}.json" for i in range(1, 7)]
paths += [ROOT / "review/low/r20261006-titles.json"]
actual_records = {}
edits = []
for path in paths:
    data = json.loads(path.read_text())
    assert not data["skipped"], (path, data["skipped"])
    edits.extend(data.get("knowledge_patches", []))
    for rid, patch in data["patches"].items():
        for field, value in patch.items():
            if field.startswith("_why"):
                continue
            assert field not in actual_records.get(rid, {}), (rid, field, "duplicate")
            assert apply_patches.validate(field, value) is None, (rid, field)
            actual_records.setdefault(rid, {})[field] = value
assert actual_records == expected_records, "Record values differ from root adjudication"
candidates, errors = apply_patches.prepare_knowledge(edits)
assert not errors, errors
expected = {p: yaml.safe_load(p.read_text()) for p in candidates}
for d in decisions:
    if d["disposition"] != "apply" or d["kind"] == "records":
        continue
    kind, rid = d["kind"], d["id"]
    if kind == "crosswalk":
        entries = expected[ROOT / "knowledge/crosswalk.yaml"]["topics"]
        entry = next(x for x in entries if x["id"] == rid)
    elif kind == "glossary":
        entry = next(x for x in expected[ROOT / "knowledge/glossary.yaml"] if x["term"] == rid)
    elif kind == "markets":
        entry = next(x for p, items in expected.items() if p.parent.name == "markets" for x in items if x["code"] == rid)
    pointer = entry
    components = d["patch_field"].split(".")
    for key in components[:-1]:
        pointer = pointer[key]
    key = components[-1]
    if isinstance(d["patch_value"], dict):
        pointer[key].update(d["patch_value"])
    else:
        pointer[key] = d["patch_value"]
assert {p: yaml.safe_load(raw) for p, raw in candidates.items()} == expected, "Unauthorized knowledge change"
for path in paths:
    destination = RUN / ("low" if path.parent.name == "low" else "patches")
    destination.mkdir(exist_ok=True)
    shutil.copyfile(path, destination / path.name)
out = {"records": len(actual_records), "record_fields": sum(map(len, actual_records.values())), "fields_by_name": dict(Counter(k for patch in actual_records.values() for k in patch)), "knowledge_files": len(candidates), "knowledge_exact_replacements": len(edits), "unauthorized_changes": 0, "validator_rejections": 0}
(RUN / "proposal-audit.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
