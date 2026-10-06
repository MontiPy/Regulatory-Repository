"""Orchestrator supplemental fixes after Phase 3 (wrong-topic template bodies, stale open_tags)."""
import sys
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "review"))
from apply_record_fixes import apply  # noqa: E402

REG = ROOT / "regulations"
STUB_MARK = "Reference stub — this repository does not hold the regulation text"

# Template bodies whose generic "Key Compliance Intent" / failure-mode text describes a
# different topic than the instrument (summaries were already corrected).
WRONG_TOPIC = [
    "cn-gb-34660",  # EMC standard; body was cyber/OTA/EDR boilerplate
    "cn-gb-8410",  # interior flammability; body was hazardous-substance/recycling boilerplate
    "cn-gb-26572-2025",  # RoHS-style substances; body was fire/shock/leakage boilerplate
    "kr-workbook-reg-0599-act-on-resource-circulation-of-electrical-and-electronic-equipment-and-vehicles",
    "gcc-gso-ece-121",  # controls/tell-tales; body was exterior-lighting boilerplate
]

fixes: dict[str, dict] = {rid: {"_stub_body": True, "open_tags": []} for rid in WRONG_TOPIC}
# Records already stubbed: their open_tags came from the wrong-topic template and are stale.
for path in sorted(REG.glob("*.md")):
    post = frontmatter.load(path)
    if STUB_MARK in post.content and post.metadata.get("open_tags"):
        fixes.setdefault(path.stem, {})["open_tags"] = []
fixes.setdefault("cn-gb-1495-2002", {})["open_tags"] = ["acoustic cover", "intake system", "exterior sound calibration"]

lines = apply(fixes, "Orchestrator supplemental — wrong-topic bodies stubbed, stale open_tags cleared")
with (ROOT / "review" / "CHANGES.md").open("a", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"{len(fixes)} records; {len(lines) - 3} changes")
