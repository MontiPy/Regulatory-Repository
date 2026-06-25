"""Apply the WEB-GROUNDED commodity re-review (pass 2) of the deferred suggestions.

Consumes the commodity-web-review workflow output (.commodity_web_changes.json) and:
  - GATES on web_access_ok: if an agent could not reach the authoritative source,
    NONE of its changes are auto-applied (routed to report-only) regardless of
    stated confidence — prevents ungrounded verdicts from writing files.
  - Applies additions at confidence in {high, medium}; removals at {high} only
    (same asymmetric bar as pass 1). HTML entities in commodity names are
    unescaped first ('Hoses &amp; lines' -> 'Hoses & lines').
  - Classifies each change as a CONFIRMED prior-deferred suggestion or a NEWLY
    DISCOVERED change, and records REFUTED deferrals (tags the web evidence kept).
  - Writes a distinct report (.commodity_web_review.md); does NOT touch pass-1 files.

Usage:
    python scripts/apply_web_review.py --dry-run
    python scripts/apply_web_review.py
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import frontmatter
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"
TAXONOMY_PATH = ROOT / "taxonomy.yaml"
WEB_CHANGES_PATH = ROOT / ".commodity_web_changes.json"
DEFERRED_PATH = ROOT / ".commodity_deferred.json"
LOG_PATH = ROOT / ".commodity_web_review.md"

APPLY_ADD_CONFIDENCE = {"high", "medium"}
APPLY_REMOVE_CONFIDENCE = {"high"}


def load_commodity_vocab() -> set[str]:
    raw = yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8")) or {}
    return set(raw.get("commodities", []))


def load_deferred_index() -> dict[str, set[tuple[str, str]]]:
    """id -> set of (kind, commodity) the prior pass deferred."""
    out: dict[str, set[tuple[str, str]]] = {}
    if DEFERRED_PATH.exists():
        for item in json.loads(DEFERRED_PATH.read_text(encoding="utf-8")):
            out[item["id"]] = {
                (d["kind"], html.unescape(d["commodity"])) for d in item.get("deferred", [])
            }
    return out


def clean(entries: list[dict]) -> list[dict]:
    for e in entries:
        if isinstance(e.get("commodity"), str):
            e["commodity"] = html.unescape(e["commodity"])
    return entries


def process(items: list[dict], vocab: set[str], deferred_idx: dict, dry_run: bool) -> dict:
    applied = []      # per-item applied changes (web-grounded)
    refuted = []      # deferred suggestions the web evidence kept (refuted)
    recommended = []  # changes NOT auto-applied (medium/low removals, low adds)
    ungrounded = []   # items where web_access_ok is false -> nothing applied
    dropped: list[str] = []
    files_changed = 0

    for it in items:
        reg_id = (it.get("id") or "").strip()
        path = REGULATIONS_DIR / f"{reg_id}.md"
        if not reg_id or not path.exists():
            dropped.append(f"{reg_id}: .md not found")
            continue

        prior = deferred_idx.get(reg_id, set())

        def tag(kind: str, commodity: str) -> str:
            return "confirmed" if (kind, commodity) in prior else "new"

        # Refuted deferrals (kept tags) come straight from the agent's verdicts.
        for v in it.get("deferred_verdicts", []) or []:
            if v.get("verdict") == "refuted":
                refuted.append({"id": reg_id, "commodity": html.unescape(v.get("commodity", "")),
                                "prior": v.get("prior_suggestion", ""), "reason": v.get("reason", "")})

        web_ok = bool(it.get("web_access_ok"))
        adds = clean(it.get("additions") or [])
        removes = clean(it.get("removals") or [])

        if not web_ok:
            ungrounded.append({"id": reg_id, "sources": it.get("sources_consulted", []),
                               "adds": adds, "removes": removes, "note": it.get("note", "")})
            continue

        post = frontmatter.load(path)
        current = list(post.get("commodities") or [])

        applied_adds, applied_removes, rec = [], [], []

        for a in adds:
            c, conf = a.get("commodity"), a.get("confidence")
            if c not in vocab:
                dropped.append(f"{reg_id}.add: '{c}' not in taxonomy")
                continue
            if c in current:
                continue
            if conf in APPLY_ADD_CONFIDENCE:
                applied_adds.append({**a, "origin": tag("add", c)})
            else:
                rec.append({"kind": "add", "origin": tag("add", c), **a})

        for r in removes:
            c, conf = r.get("commodity"), r.get("confidence")
            if c not in current:
                continue
            if conf in APPLY_REMOVE_CONFIDENCE:
                applied_removes.append({**r, "origin": tag("remove", c)})
            else:
                rec.append({"kind": "remove", "origin": tag("remove", c), **r})

        remove_set = {r["commodity"] for r in applied_removes}
        add_list = [a["commodity"] for a in applied_adds]
        new_commodities = [c for c in current if c not in remove_set] + [
            c for c in add_list if c not in current
        ]

        if rec:
            recommended.append({"id": reg_id, "changes": rec})

        if new_commodities != current:
            files_changed += 1
            applied.append({"id": reg_id, "before": current, "after": new_commodities,
                            "added": applied_adds, "removed": applied_removes,
                            "sources": it.get("sources_consulted", []), "note": it.get("note", "")})
            if not dry_run:
                post["commodities"] = new_commodities
                path.write_text(frontmatter.dumps(post), encoding="utf-8")

    return {"applied": applied, "refuted": refuted, "recommended": recommended,
            "ungrounded": ungrounded, "dropped": dropped, "files_changed": files_changed}


def write_log(s: dict, total: int, grounded: int, dry_run: bool) -> None:
    L: list[str] = ["# Commodity tag review — web-grounded pass (deferred items)", ""]
    L.append(f"Mode: **{'DRY-RUN (no files written)' if dry_run else 'applied to frontmatter'}**  ")
    L.append(f"Items reviewed: **{total}** (web-grounded: {grounded})  ")
    L.append(f"Files changed: **{s['files_changed']}**  ")
    L.append("Gate: items without verified web access are report-only. "
             "Additions applied at high+medium; removals at high only. "
             "Each change tagged `[confirmed]` (a prior deferred suggestion) or `[new]` (discovered via web).")
    L.append("")

    L.append("## 1. Applied — web-grounded changes")
    L.append("")
    if not s["applied"]:
        L.append("_None._")
    for e in s["applied"]:
        L.append(f"### {e['id']}")
        L.append(f"- before: `{e['before']}`")
        L.append(f"- after:  `{e['after']}`")
        for a in e["added"]:
            L.append(f"- **+ {a['commodity']}** ({a['confidence']}, [{a['origin']}]) — {a['reason']}")
        for r in e["removed"]:
            L.append(f"- **− {r['commodity']}** ({r['confidence']}, [{r['origin']}]) — {r['reason']}")
        if e.get("sources"):
            L.append(f"- sources: {', '.join(str(x) for x in e['sources'][:4])}")
        L.append("")

    L.append("## 2. Refuted deferrals — prior suggestion overturned, tag KEPT")
    L.append("")
    if not s["refuted"]:
        L.append("_None._")
    for r in s["refuted"]:
        L.append(f"- `{r['id']}` — kept **{r['commodity']}**: {r['reason']}")
    L.append("")

    L.append("## 3. Recommended, NOT auto-applied (web medium/low — your call)")
    L.append("")
    if not s["recommended"]:
        L.append("_None._")
    for e in s["recommended"]:
        L.append(f"### {e['id']}")
        for c in e["changes"]:
            sign = "+" if c["kind"] == "add" else "−"
            L.append(f"- {sign} {c['commodity']} ({c['confidence']}, [{c['origin']}]) — {c['reason']}")
        L.append("")

    L.append("## 4. Ungrounded — web access failed, nothing applied (manual review)")
    L.append("")
    if not s["ungrounded"]:
        L.append("_None — all reviewed items had web access._")
    for e in s["ungrounded"]:
        chg = [f"−{r['commodity']}" for r in e["removes"]] + [f"+{a['commodity']}" for a in e["adds"]]
        L.append(f"- `{e['id']}` — proposed {chg or 'no change'}; {e['note']}")
    L.append("")

    if s["dropped"]:
        L.append("## Dropped (out-of-vocab / missing file)")
        L.append("")
        for d in s["dropped"]:
            L.append(f"- {d}")
        L.append("")

    LOG_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--changes", default=str(WEB_CHANGES_PATH))
    args = ap.parse_args()

    payload = json.loads(Path(args.changes).read_text(encoding="utf-8"))
    items = payload.get("items", payload) if isinstance(payload, dict) else payload
    total = payload.get("reviewed", len(items)) if isinstance(payload, dict) else len(items)
    grounded = sum(1 for it in items if it.get("web_access_ok"))

    vocab = load_commodity_vocab()
    deferred_idx = load_deferred_index()
    s = process(items, vocab, deferred_idx, args.dry_run)
    write_log(s, total, grounded, args.dry_run)

    print(f"{'[dry-run] ' if args.dry_run else ''}files changed: {s['files_changed']}")
    print(f"applied: {len(s['applied'])}, refuted/kept: {len(s['refuted'])}, "
          f"recommended: {len(s['recommended'])}, ungrounded: {len(s['ungrounded'])}, "
          f"dropped: {len(s['dropped'])}")
    print(f"log: {LOG_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
