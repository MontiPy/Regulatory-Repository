"""Keep adjudicated raw documents and all text; archive bulky unadjudicated EU binaries."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
E = RUN / "evidence"
archive = Path("/tmp/regulatory-external-eu-binary-archive")
archive.mkdir(exist_ok=True)
keep = {"32017R1151", "32019R2144", "32024R1257", "32026R1738", "42026X1086", "52025PC0995"}
rows = json.loads((E / "eu-publications-sources.json").read_text())
https_rows = {r["name"].removeprefix("https-"): r for r in json.loads((E / "eu-https-sources.json").read_text())}
manifest = []
for row in rows:
    celex = row["name"].removeprefix("eu-publication-")
    raw = ROOT / row["raw_path"]
    if celex not in keep and raw.exists() and raw.stat().st_size > 100_000:
        target = archive / raw.name
        shutil.move(raw, target)
        row["raw_path"] = str(target)
        row["snapshot_policy"] = "Original compressed response archived in /tmp; source hash and extracted text retained in this run. No technical completeness/currency adjudication."
        manifest.append({"celex": celex, "original_sha256": row["sha256"], "archived_raw_path": str(target), "retained_text_path": row["text_path"]})
    elif celex in keep and row["availability"] == "response_retrieved":
        # Preserve HTTPS-authenticated copies for every adjudicated EU publication.
        secure = https_rows[row["name"]]
        assert secure["sha256"] == row["sha256"] and secure["url"].startswith("https://")
        destination = E / "sources" / (secure["name"] + ".raw.gz")
        shutil.copyfile(secure["raw_path"], destination)
        secure["raw_path"] = str(destination.relative_to(ROOT))
        secure["text_path"] = row["text_path"]
for name in ("br-contran215-original.txt",):
    # An older extraction treated binary DOC bytes as HTML; discard its invalid text.
    p = E / "sources" / name
    if p.exists():
        p.write_text("Binary Microsoft Word document retrieved. Text extraction was not performed; use the official DOC.\n")
(E / "eu-publications-sources.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
(E / "eu-https-sources.json").write_text(json.dumps(list(https_rows.values()), ensure_ascii=False, indent=2) + "\n")
(E / "binary-retention.json").write_text(json.dumps({"policy": "All extracted text and response hashes retained. Adjudicated EU documents retain both original and matching HTTPS raw copies. Bulky unadjudicated EU responses archived outside the review tree.", "archived": manifest}, ensure_ascii=False, indent=2) + "\n")
print(f"Archived {len(manifest)} bulky unadjudicated EU responses; adjudicated originals retained.")
