"""Merge staged re-pulls (scripts/pull_staged.py) into regulations/ — body text only.

All curated metadata (title, summary, status, tags, UN equivalents, notes) is kept. A staged
body replaces the current one only when it is full regulation text (build.content_kind ==
"full") and either the current body is not, or the text changed. Bodies that got worse
(the source returned a link/index page) are never merged. Summaries whose body changed are
left with their old summary_hash so the site flags them as stale until re-checked.

Usage: python scripts/merge_staged.py STAGE_DIR [--apply] [--report PATH]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build import clean_body, content_kind  # noqa: E402

REG = ROOT / "regulations"
WORD = re.compile(r"[A-Za-z]{5,}")


def kind(post) -> str:
    return content_kind(clean_body(post.content, str(post.metadata.get("source_api", ""))))


def title_overlap(title: str, body: str) -> float:
    words = {w.lower() for w in WORD.findall(title or "")}
    if not words:
        return 1.0
    low = body.lower()
    return sum(w in low for w in words) / len(words)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    stats: Counter = Counter()
    rows: list[str] = []
    for staged in sorted(args.stage.glob("*/*.md")):
        current = REG / staged.name
        if not current.exists():
            stats["new record (ignored)"] += 1
            continue
        new, old = frontmatter.load(staged), frontmatter.load(current)
        kn, ko = kind(new), kind(old)
        if kn != "full":
            stats[f"staged {kn} — kept current"] += 1
            continue
        if ko == "full" and old.metadata.get("translation_status") == "translated":
            stats["current is an English translation — kept"] += 1
            continue
        if new.content.strip() == old.content.strip():
            stats["unchanged"] += 1
            continue
        overlap = title_overlap(str(old.metadata.get("title", "")), new.content)
        action = "upgraded to full text" if ko != "full" else "text refreshed"
        same_source = new.metadata.get("source_url") == old.metadata.get("source_url")
        if overlap < 0.3 and not (ko == "full" and same_source):
            stats["held: title words absent from new text"] += 1
            rows.append(f"| `{staged.stem}` | HELD ({overlap:.0%} title match) | {ko} → {kn} |")
            continue
        stats[action] += 1
        rows.append(f"| `{staged.stem}` | {action} | {ko} → {kn}, {len(old.content)} → {len(new.content)} chars |")
        if args.apply:
            old.content = new.content
            old.metadata["last_pulled"] = new.metadata.get("last_pulled")
            if ko != "full" and new.metadata.get("source_url"):
                old.metadata["source_url"] = new.metadata["source_url"]
            out = frontmatter.dumps(old)
            current.write_text(out if out.endswith("\n") else out + "\n", encoding="utf-8")
    for k, v in sorted(stats.items()):
        print(f"{v:4d}  {k}")
    if args.report:
        args.report.write_text("| Record | Action | Detail |\n|---|---|---|\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
