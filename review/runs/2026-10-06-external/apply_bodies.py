"""Apply prepared body replacements only when every original body hash still matches."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "review"))
from apply_record_fixes import apply

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
proposals = json.loads((RUN / "body-proposals.json").read_text())
fixes = {}
for row in proposals:
    post = frontmatter.load(ROOT / "regulations" / (row["id"] + ".md"))
    assert hashlib.sha256(post.content.encode()).hexdigest() == row["expected_body_sha256"], row["id"]
    new = (ROOT / row["proposed_body"]).read_text().strip()
    assert new and new != post.content
    assert all(source["sha256"] and source["url"].startswith("https://") for source in row["sources"])
    changes = {"_body_replace": [(post.content, new)]}
    if row["id"] in {"eu-32017r1151", "br-contran-37", "br-contran-498", "br-contran-764", "br-contran-924", "br-senatran-990"}:
        changes["last_pulled"] = max(s["retrieved_at"] for s in row["sources"])
    fixes[row["id"]] = changes
print(f"{len(fixes)} body proposals pass preimage and source checks.")
if args.apply:
    lines = apply(fixes, "External review — authenticated source text and isolated applicability repairs")
    with (ROOT / "review/CHANGES.md").open("a") as fh:
        fh.write("\n".join(lines) + "\n")
    outcomes = []
    for row in proposals:
        post = frontmatter.load(ROOT / "regulations" / (row["id"] + ".md"))
        outcomes.append({**row, "applied_body_sha256": hashlib.sha256(post.content.encode()).hexdigest(),
                         "summary_hash": post["summary_hash"]})
    (RUN / "evidence/body-results.json").write_text(json.dumps(outcomes, ensure_ascii=False, indent=2) + "\n")
    print(f"Applied {len(fixes)} body proposals; summary hashes refreshed.")
