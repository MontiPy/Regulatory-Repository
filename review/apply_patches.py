"""Validate and apply patch-writer output (review/patches/<group>.json) to regulations/*.md.

Every proposed value is validated before anything is written:
  * only whitelisted fields;
  * systems / commodities / vehicle_categories / status must be taxonomy values;
  * un_equivalent(_ai) items must match ^UN R\\d+[A-Z]?$;
  * effective_date must be YYYY-MM-DD; strings must be non-empty and free of "..." truncation.
Invalid fields are rejected (reported, not applied); the rest of the record's patch still applies.

Usage (repo root): python review/apply_patches.py [--dry-run] [--skip ID ...]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "review"))
sys.path.insert(0, str(ROOT))
from apply_record_fixes import apply  # noqa: E402

TAX = yaml.safe_load((ROOT / "taxonomy.yaml").read_text(encoding="utf-8"))
UN_RE = re.compile(r"^UN R\d+[A-Z]?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LIST_TAX = {"systems": "systems", "commodities": "commodities", "vehicle_categories": "vehicle_categories"}
STRING_FIELDS = {"title", "summary", "status_note", "citation", "source_url"}
ALLOWED = set(LIST_TAX) | STRING_FIELDS | {"status", "un_equivalent", "effective_date", "_stub_body", "_confirmed"}


def validate(field: str, value) -> str | None:
    if field not in ALLOWED:
        return "field not allowed"
    if field in LIST_TAX:
        if not isinstance(value, list):
            return "must be a list"
        bad = [v for v in value if v not in TAX[LIST_TAX[field]]]
        return f"not in taxonomy: {bad}" if bad else None
    if field in ("un_equivalent", "un_equivalent_ai"):
        if not isinstance(value, list):
            return "must be a list"
        bad = [v for v in value if not (isinstance(v, str) and UN_RE.match(v))]
        return f"bad UN refs: {bad}" if bad else None
    if field == "status":
        return None if value in TAX["statuses"] else f"status '{value}' not allowed"
    if field == "effective_date":
        if not isinstance(value, str) or not DATE_RE.fullmatch(value):
            return "bad date"
        try:
            date.fromisoformat(value)
        except ValueError:
            return "invalid calendar date"
        return None
    if field in ("_stub_body", "_confirmed"):
        return None if value is True else "must be true"
    if field in STRING_FIELDS:
        if not isinstance(value, str) or not value.strip():
            return "empty string"
        if value.rstrip().endswith("...") or value.rstrip().endswith("…"):
            return "truncated text"
        if field == "source_url":
            parsed = urlparse(value)
            if not re.fullmatch(r"https?://[^\s]+", value) or not parsed.hostname or parsed.username:
                return "bad URL"
        if field == "summary" and len(value) > 700:
            return "summary too long"
    return None


def prepare_knowledge(edits: list[dict]) -> tuple[dict[Path, str], list[str]]:
    """Validate exact, unique replacements against the whole knowledge schema.

    No YAML is written until the candidate corpus validates. Exact replacements
    retain comments and formatting and make stale proposals fail closed.
    """
    allowed = {"crosswalk.yaml", "glossary.yaml"} | {
        f"markets/{p.name}" for p in (ROOT / "knowledge/markets").glob("*.yaml")
    }
    candidates: dict[Path, str] = {}
    errors: list[str] = []
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) - {"file", "old", "new", "_why"}:
            errors.append("knowledge: invalid edit schema")
            continue
        name, old, new = (edit.get(k) for k in ("file", "old", "new"))
        if name not in allowed or not all(isinstance(v, str) and v for v in (old, new, edit.get("_why"))):
            errors.append(f"knowledge {name}: invalid path, replacement or evidence reason")
            continue
        path = ROOT / "knowledge" / name
        raw = candidates.get(path, path.read_text(encoding="utf-8"))
        if raw.count(old) != 1:
            errors.append(f"knowledge {name}: expected exactly one occurrence of old text")
            continue
        if new.rstrip().endswith(("...", "…")):
            errors.append(f"knowledge {name}: truncated text")
            continue
        candidates[path] = raw.replace(old, new, 1)
    if errors:
        return {}, errors
    if not candidates:
        return {}, []
    from scripts import knowledge
    attrs = ("KNOWLEDGE_DIR", "MARKETS_DIR", "CROSSWALK_PATH", "GLOSSARY_PATH")
    originals = {key: getattr(knowledge, key) for key in attrs}
    with tempfile.TemporaryDirectory(prefix="regulatory-knowledge-") as temp:
        staged = Path(temp) / "knowledge"
        shutil.copytree(ROOT / "knowledge", staged)
        for path, raw in candidates.items():
            (staged / path.relative_to(ROOT / "knowledge")).write_text(raw, encoding="utf-8")
        knowledge.KNOWLEDGE_DIR = staged
        knowledge.MARKETS_DIR = staged / "markets"
        knowledge.CROSSWALK_PATH = staged / "crosswalk.yaml"
        knowledge.GLOSSARY_PATH = staged / "glossary.yaml"
        try:
            _, schema_errors = knowledge.build_knowledge(
                {p.stem for p in (ROOT / "regulations").glob("*.md")}, set(TAX["regions"])
            )
            errors.extend(f"knowledge: {e}" for e in schema_errors)
        except (yaml.YAMLError, TypeError, KeyError, ValueError, AttributeError) as exc:
            errors.append(f"knowledge: {exc}")
        finally:
            for key, value in originals.items():
                setattr(knowledge, key, value)
    return ({}, errors) if errors else (candidates, [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip", nargs="*", default=[], help="record ids to leave untouched (orchestrator veto)")
    ap.add_argument("--dir", default="patches", help="sub-directory of review/ holding <group>.json patch files")
    ap.add_argument("--label", default="Phase 3 — medium/high findings via patch writers (validated)")
    args = ap.parse_args()
    fixes: dict[str, dict] = {}
    rejected: list[str] = []
    conflicts: set[tuple[str, str]] = set()
    knowledge_edits: list[dict] = []
    for path in sorted((ROOT / "review" / args.dir).glob("*.json")):
        if path.name.endswith(".input.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        knowledge_edits.extend(data.get("knowledge_patches") or [])
        for rid, patch in (data.get("patches") or {}).items():
            if rid in args.skip:
                rejected.append(f"{rid}: vetoed by orchestrator")
                continue
            if not (ROOT / "regulations" / f"{rid}.md").exists():
                rejected.append(f"{rid}: record does not exist")
                continue
            clean = {}
            for field, value in patch.items():
                if field.startswith("_why"):
                    continue
                err = validate(field, value)
                if err:
                    rejected.append(f"{rid}.{field}: {err}")
                else:
                    if (rid, field) in conflicts:
                        rejected.append(f"{rid}.{field}: conflicting proposals")
                    elif field in fixes.get(rid, {}) and fixes[rid][field] != value:
                        rejected.append(f"{rid}.{field}: conflicting proposals")
                        fixes[rid].pop(field)
                        conflicts.add((rid, field))
                    else:
                        clean[field] = value
            if clean.get("_stub_body") and "summary" not in clean:
                rejected.append(f"{rid}._stub_body: needs a corrected summary — skipped")
                clean.pop("_stub_body")
            if clean:
                fixes.setdefault(rid, {}).update(clean)
    knowledge_candidates, knowledge_errors = prepare_knowledge(knowledge_edits)
    rejected.extend(knowledge_errors)
    print(f"{len(fixes)} records, {sum(len(v) for v in fixes.values())} fields valid; {len(knowledge_candidates)} knowledge files valid; {len(rejected)} rejected")
    for r in rejected:
        print("  REJECTED", r)
    if args.dry_run:
        return 0
    lines = apply(fixes, args.label)
    for path, raw in knowledge_candidates.items():
        path.write_text(raw, encoding="utf-8")
    if knowledge_candidates:
        lines += ["", "Knowledge edits (exact text; full schema and record references validated):"]
        for edit in knowledge_edits:
            lines.append(f"- `{edit['file']}`: {edit['_why']}")
    if rejected:
        lines += ["", "Rejected by validator / orchestrator:", *[f"- {r}" for r in rejected]]
    with (ROOT / "review" / "CHANGES.md").open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"applied; {len(lines)} log lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
