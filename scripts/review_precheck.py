"""Deterministic (no-LLM) consistency checks over regulations/*.md.

Flags mechanical problems cheaply before any model review:
  * body-thin      — a live-connector record whose body is too short to be regulation text
  * status-text    — status in-force but the body says reserved / removed / repealed / superseded
  * number-mismatch— the standard number in id/title/summary disagrees with the citation
  * weak-title     — title is just an id/CELEX/section label with no subject
  * dup-citation   — two records share one citation
  * bad-url        — source_url not http(s)

Usage: python scripts/review_precheck.py [--out review/precheck.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
REG_DIR = ROOT / "regulations"

# Sources whose connector is supposed to return the regulation text itself.
FULL_TEXT_SOURCES = {"ecfr", "eurlex", "justice_ca", "au_legislation", "egov_jp", "law_go_kr", "brazil", "unece"}
THIN_BODY_CHARS = 600

STATUS_WORDS = re.compile(
    r"\[\s*reserved\s*\]|\bremoved and reserved\b|\bhereby repealed\b|\bis repealed\b|\bno longer in force\b|"
    r"\bsuperseded by\b|\brevoked\b|废止|폐지|廃止",
    re.IGNORECASE,
)
WEAK_TITLE = re.compile(
    r"^(?:3\d{4}[RLD]\d{4}|MVSR(?: C\.R\.C\.,_c\._1038)? s\. ?[\d.]+|MVSR SOR-\d{4}-\d+|KMVSS Article [\d-]+|JVSR Article [\d_]+)$"
)


def _gb_number(text: str) -> str | None:
    m = re.search(r"\bGB(?:/T)?\s?(\d{3,5}(?:\.\d+)?)", text or "")
    return m.group(1) if m else None


def _adr_number(text: str) -> str | None:
    m = re.search(r"\bADR\s?(\d{1,3})/\d{2}", text or "")
    return m.group(1) if m else None


def _fmvss_number(text: str) -> str | None:
    m = re.search(r"(?:571\.|Standard No\.\s?|FMVSS\s?)(\d{3}[a-z]?)", text or "")
    return m.group(1) if m else None


def number_mismatches(meta: dict, body: str) -> list[str]:
    out: list[str] = []
    cid, cit, title, summary = meta.get("id", ""), str(meta.get("citation", "")), str(meta.get("title", "")), str(meta.get("summary", ""))
    src = meta.get("source_api")
    if src == "china":
        c = _gb_number(cit)
        idnum = re.search(r"cn-gb(?:-t)?-(\d+)", cid)
        if c and idnum and c.split(".")[0] != idnum.group(1):
            out.append(f"id GB {idnum.group(1)} vs citation {cit}")
        s = _gb_number(summary)
        if c and s and s != c and not s.startswith(c.split(".")[0]):
            out.append(f"summary cites GB {s} but citation is {cit}")
    if src == "au_legislation":
        c, t = _adr_number(cit), _adr_number(title)
        if c and t and c != t:
            out.append(f"title ADR {t} vs citation ADR {c}")
    if src == "ecfr" and cid.startswith("us-fmvss-"):
        idn = cid.removeprefix("us-fmvss-")
        c = _fmvss_number(cit) or ""
        t = _fmvss_number(title) or ""
        if c and c != idn:
            out.append(f"id FMVSS {idn} vs citation {cit}")
        if t and t != idn:
            out.append(f"id FMVSS {idn} vs title {title[:60]}")
    if src == "unece":
        m = re.match(r"ece-r(\d+)", cid)
        t = re.search(r"Regulation No\.\s?(\d+)", title + " " + body[:300])
        if m and t and m.group(1) != t.group(1):
            out.append(f"id R{m.group(1)} vs text R{t.group(1)}")
    return out


def run() -> dict:
    findings: list[dict] = []
    by_citation: dict[str, list[str]] = defaultdict(list)
    for path in sorted(REG_DIR.glob("*.md")):
        post = frontmatter.load(path)
        meta, body = post.metadata, post.content
        rid, src = meta.get("id", path.stem), meta.get("source_api")

        def flag(kind: str, detail: str) -> None:
            findings.append({"id": rid, "check": kind, "detail": detail, "source_api": src})

        by_citation[str(meta.get("citation", "")).strip().lower()].append(rid)
        if src in FULL_TEXT_SOURCES and len(body.strip()) < THIN_BODY_CHARS:
            flag("body-thin", f"{len(body.strip())} chars from a full-text connector ({src})")
        if meta.get("status") == "in-force":
            m = STATUS_WORDS.search(body[:4000])
            if m:
                flag("status-text", f"status in-force but body says '{m.group(0)}' near start")
        for issue in number_mismatches(meta, body):
            flag("number-mismatch", issue)
        if WEAK_TITLE.match(str(meta.get("title", "")).strip()):
            flag("weak-title", f"title '{meta.get('title')}' has no subject")
        url = str(meta.get("source_url", ""))
        if url and not url.startswith(("https://", "http://")):
            flag("bad-url", url)
    for cit, ids in by_citation.items():
        if cit and len(ids) > 1:
            for rid in ids:
                findings.append({"id": rid, "check": "dup-citation", "detail": f"citation shared with {', '.join(i for i in ids if i != rid)}", "source_api": None})
    counts: dict[str, int] = defaultdict(int)
    for f in findings:
        counts[f["check"]] += 1
    return {"counts": dict(sorted(counts.items())), "findings": findings}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="review/precheck.json")
    args = ap.parse_args()
    result = run()
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["counts"]), f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
