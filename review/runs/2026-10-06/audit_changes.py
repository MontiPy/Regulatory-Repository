"""Verify final content changes against approved JSON and the recorded baseline."""
import json
import subprocess
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
BASE = "faefa1c5f239f5e2a6bcf28ce54ebd0b0c3c8a92"
expected = {}
for folder in ("patches", "low", "verify"):
    for path in (RUN / folder).glob("*.json"):
        for rid, values in json.loads(path.read_text())["patches"].items():
            expected.setdefault(rid, {}).update({k: v for k, v in values.items() if not k.startswith("_why")})
paths = subprocess.check_output(["git", "diff", "--name-only", BASE, "--", "regulations/"], cwd=ROOT, text=True).splitlines()
assert {Path(p).stem for p in paths} == set(expected), "Changed record set differs from approved set"
changes = []
for rel in paths:
    old = frontmatter.loads(subprocess.check_output(["git", "show", BASE + ":" + rel], cwd=ROOT, text=True))
    new = frontmatter.load(ROOT / rel)
    rid = Path(rel).stem
    allowed = {k for k in expected[rid] if not k.startswith("_")} | {"summary_hash", "summary_generated_at"}
    fields = {k: {"before": old.get(k), "after": new.get(k)} for k in old.metadata.keys() | new.metadata.keys() if old.get(k) != new.get(k)}
    assert fields.keys() <= allowed, (rid, "unexpected fields", fields.keys() - allowed)
    for field, value in expected[rid].items():
        if not field.startswith("_"):
            assert new.get(field) == value, (rid, field, "value differs")
    assert (old.content != new.content) == bool(expected[rid].get("_stub_body")), (rid, "unexpected body edit")
    changes.append({"id": rid, "path": rel, "body_changed": old.content != new.content, "fields": fields})
(RUN / "record-changes.json").write_text(json.dumps(changes, indent=2, ensure_ascii=False) + "\n")
print(f"Final audit: {len(changes)} records, {sum(c['body_changed'] for c in changes)} authorized body replacements, zero unauthorized edits.")
