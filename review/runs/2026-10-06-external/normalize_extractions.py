"""Remove extraction-only trailing whitespace and record final body hashes."""
import hashlib
import json
import sys
from pathlib import Path
import frontmatter

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "review"))
from apply_record_fixes import apply

proposals = json.loads((RUN / "body-proposals.json").read_text())
fixes = {}
for row in proposals:
    path = ROOT / "regulations" / (row["id"] + ".md")
    post = frontmatter.load(path)
    normalized = "\n".join(line.rstrip() for line in post.content.splitlines()).strip()
    if normalized != post.content:
        fixes[row["id"]] = {"_body_replace": [(post.content, normalized)]}
        (ROOT / row["proposed_body"]).write_text(normalized + "\n")
if fixes:
    lines = apply(fixes, "External review — normalize extracted trailing whitespace (wording preserved)")
    with (ROOT / "review/CHANGES.md").open("a") as fh:
        fh.write("\n".join(lines) + "\n")
results = []
for row in proposals:
    post = frontmatter.load(ROOT / "regulations" / (row["id"] + ".md"))
    results.append({**row, "applied_body_sha256": hashlib.sha256(post.content.encode()).hexdigest(),
                    "summary_hash": post["summary_hash"],
                    "normalization": "Trailing whitespace stripped; source wording preserved. Raw snapshots remain unmodified."})
(RUN / "evidence/body-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
print(f"Normalized trailing whitespace in {len(fixes)} imported bodies.")
