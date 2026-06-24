"""Apply the AI commodity-tag review back into .md frontmatter.

Consumes the JSON produced by the commodity-tag-review workflow (.commodity_review_changes.json),
re-judges against the *actual* current frontmatter, and applies only confident changes:

  - additions  : applied at confidence in {high, medium}
  - removals   : applied at confidence == high only   (asymmetric: dropping a
                 correct tag is worse than missing one)

Everything not auto-applied (low-confidence adds, medium/low removals) is recorded
in the change log as a suggestion for human review. Only the `commodities` field is
touched; systems / vehicle_categories / status are left untouched. Out-of-vocab
values are dropped and logged (same policy as tag_import.py).

Usage:
    python scripts/apply_commodity_review.py --dry-run
    python scripts/apply_commodity_review.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import frontmatter
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"
TAXONOMY_PATH = ROOT / "taxonomy.yaml"
CHANGES_PATH = ROOT / ".commodity_review_changes.json"
IDS_PATH = ROOT / ".commodity_review_ids.txt"
LOG_PATH = ROOT / ".commodity_review.md"

APPLY_ADD_CONFIDENCE = {"high", "medium"}
APPLY_REMOVE_CONFIDENCE = {"high"}


def load_commodity_vocab() -> set[str]:
    raw = yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8")) or {}
    return set(raw.get("commodities", []))


def reg_path(reg_id: str) -> Path:
    return REGULATIONS_DIR / f"{reg_id}.md"


def apply_changes(changes: list[dict], vocab: set[str], dry_run: bool) -> dict:
    applied_log: list[dict] = []
    deferred_log: list[dict] = []
    dropped: list[str] = []
    files_changed = 0

    for item in changes:
        reg_id = (item.get("id") or "").strip()
        path = reg_path(reg_id)
        if not reg_id or not path.exists():
            dropped.append(f"{reg_id}: .md not found")
            continue

        post = frontmatter.load(path)
        current = list(post.get("commodities") or [])

        adds = item.get("additions") or []
        removes = item.get("removals") or []

        applied_adds, applied_removes = [], []
        deferred = []

        for a in adds:
            c, conf = a.get("commodity"), a.get("confidence")
            if c not in vocab:
                dropped.append(f"{reg_id}.add: '{c}' not in taxonomy")
                continue
            if c in current:
                continue  # already present
            if conf in APPLY_ADD_CONFIDENCE:
                applied_adds.append(a)
            else:
                deferred.append({"kind": "add", **a})

        for r in removes:
            c, conf = r.get("commodity"), r.get("confidence")
            if c not in current:
                continue  # nothing to remove
            if conf in APPLY_REMOVE_CONFIDENCE:
                applied_removes.append(r)
            else:
                deferred.append({"kind": "remove", **r})

        remove_set = {r["commodity"] for r in applied_removes}
        add_list = [a["commodity"] for a in applied_adds]
        new_commodities = [c for c in current if c not in remove_set] + [
            c for c in add_list if c not in current
        ]

        if deferred:
            deferred_log.append({"id": reg_id, "note": item.get("note", ""), "deferred": deferred})

        if new_commodities != current:
            files_changed += 1
            applied_log.append({
                "id": reg_id,
                "note": item.get("note", ""),
                "before": current,
                "after": new_commodities,
                "added": [a for a in applied_adds],
                "removed": [r for r in applied_removes],
            })
            if not dry_run:
                post["commodities"] = new_commodities
                path.write_text(frontmatter.dumps(post), encoding="utf-8")

    return {
        "applied": applied_log,
        "deferred": deferred_log,
        "dropped": dropped,
        "files_changed": files_changed,
    }


def cross_region_divergence() -> list[dict]:
    """Group all reviewed regs by un_equivalent_ai UN R number; flag groups whose
    members carry differing commodity sets (classifier rule #3 cannot be enforced
    per-batch). Reads files by explicit id path (OneDrive dir-listing is flaky)."""
    ids = [l.strip() for l in IDS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    groups: dict[str, list[tuple[str, frozenset]]] = {}
    for reg_id in ids:
        path = reg_path(reg_id)
        if not path.exists():
            continue
        meta = frontmatter.load(path).metadata
        commodities = frozenset(meta.get("commodities") or [])
        for un in (meta.get("un_equivalent_ai") or []):
            groups.setdefault(str(un).strip(), []).append((reg_id, commodities))

    divergent = []
    for un, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        distinct = {m[1] for m in members}
        if len(distinct) > 1:
            divergent.append({
                "un": un,
                "members": [{"id": m[0], "commodities": sorted(m[1])} for m in members],
            })
    return divergent


def write_log(summary: dict, divergent: list[dict], dry_run: bool) -> None:
    lines = ["# Commodity tag review", ""]
    mode = "DRY-RUN (no files written)" if dry_run else "applied to frontmatter"
    lines.append(f"Mode: **{mode}**  ")
    lines.append(f"Files changed: **{summary['files_changed']}**  ")
    lines.append("Policy: additions applied at high+medium confidence; removals at high confidence only.")
    lines.append("")

    lines.append("## Applied changes")
    lines.append("")
    if not summary["applied"]:
        lines.append("_None._")
    for e in summary["applied"]:
        lines.append(f"### {e['id']}")
        lines.append(f"- before: `{e['before']}`")
        lines.append(f"- after:  `{e['after']}`")
        for a in e["added"]:
            lines.append(f"- **+ {a['commodity']}** ({a['confidence']}) — {a['reason']}")
        for r in e["removed"]:
            lines.append(f"- **− {r['commodity']}** ({r['confidence']}) — {r['reason']}")
        if e["note"]:
            lines.append(f"- _{e['note']}_")
        lines.append("")

    lines.append("## Suggestions NOT auto-applied (review manually)")
    lines.append("")
    if not summary["deferred"]:
        lines.append("_None._")
    for e in summary["deferred"]:
        lines.append(f"### {e['id']}")
        for d in e["deferred"]:
            sign = "+" if d["kind"] == "add" else "−"
            lines.append(f"- {sign} {d['commodity']} ({d['confidence']}) — {d['reason']}")
        lines.append("")

    lines.append("## Cross-region divergence (same UN R number, different commodities)")
    lines.append("")
    lines.append("_Flagged for review; not auto-reconciled (rule: identical subject matter should share tags)._")
    lines.append("")
    if not divergent:
        lines.append("_No divergence found._")
    for g in divergent:
        lines.append(f"### {g['un']}")
        for m in g["members"]:
            lines.append(f"- `{m['id']}`: {m['commodities']}")
        lines.append("")

    if summary["dropped"]:
        lines.append("## Dropped (out-of-vocab / missing file)")
        lines.append("")
        for d in summary["dropped"]:
            lines.append(f"- {d}")
        lines.append("")

    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print/log what would change; write no .md files.")
    ap.add_argument("--changes", default=str(CHANGES_PATH), help="Path to workflow changes JSON.")
    args = ap.parse_args()

    changes_path = Path(args.changes)
    if not changes_path.exists():
        print(f"Changes file not found: {changes_path}", file=sys.stderr)
        return 1

    payload = json.loads(changes_path.read_text(encoding="utf-8"))
    changes = payload.get("changed", payload) if isinstance(payload, dict) else payload

    vocab = load_commodity_vocab()
    summary = apply_changes(changes, vocab, args.dry_run)
    divergent = cross_region_divergence()
    write_log(summary, divergent, args.dry_run)

    print(f"{'[dry-run] ' if args.dry_run else ''}files changed: {summary['files_changed']}")
    print(f"applied entries: {len(summary['applied'])}, deferred: {len(summary['deferred'])}, "
          f"dropped: {len(summary['dropped'])}, divergent UN groups: {len(divergent)}")
    print(f"log: {LOG_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
