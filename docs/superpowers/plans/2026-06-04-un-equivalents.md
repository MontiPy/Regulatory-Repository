# UN Equivalents (grounded + AI-suggested) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate cross-market UN regulation equivalents on every record — grounded citations extracted deterministically from the text, plus LLM-inferred cross-market links stored and displayed separately as "AI-suggested — verify against source" — and make every equivalent a clickable link to the corresponding UN/ECE record.

**Architecture:** Two provenance-separated frontmatter fields. `un_equivalent` holds grounded UN R numbers scanned verbatim from the body (pure-Python extractor, no API). `un_equivalent_ai` holds LLM-inferred cross-market equivalents (Anthropic Batch API, Haiku), never commingled with grounded values. `related` is **derived in build.py** from grounded shared-UN clusters (AI stays out of the hard graph), and `build.py` emits a `un_index` map (UN R string → ECE record id) so the reader can render both grounded and AI equivalents as links. The reader shows grounded equivalents as ordinary chips and AI equivalents in a visually distinct, explicitly-labelled block; both link to the target ECE record when one exists.

**Tech Stack:** Python 3.14, `python-frontmatter`, PyYAML, `anthropic` (Batch API), pytest; vanilla JS reader (`assets/app.js`), CSS (`assets/styles.css`).

**Build order (advisor-directed):** Ship and verify the grounded path (Tasks 1→2→3) green first; layer the AI batch (Tasks 4→5) on top. Same deliverable, safer checkpoint.

**Key decisions (folded in from design review):**
1. AI-suggested chips are **clickable links** to the target record (marked unverified) — FMVSS 208's only path to ECE R94 is its AI chip, so text-only would dead-end the headline use case.
2. Grounded extraction keeps any syntactically-valid `UN R\d+[a-z]?` (number ≥ 1; `R0` dropped as junk) **regardless of corpus coverage** — a grounded citation is a true fact. A `related` *link* is only created when the target record exists. Junk filter = format/sanity, not completeness.
3. `related` is derived from **grounded** edges only; reverse-edge fan-out is capped at `MAX_RELATED = 12`.
4. Inference prompt makes "none" first-class and caps suggestions at 1–2; empty is expected and correct.

---

## File Structure

- `scripts/build.py` (modify) — register/validate `un_equivalent_ai`; build `un_index`; derive `related`; emit both into the bundle.
- `scripts/un_refs.py` (create) — shared helpers: parse ECE id → UN number, normalize a UN R string, scan body text for grounded citations. Imported by the extractor, the inference script, and build.py so the number↔id logic lives in one place.
- `scripts/extract_un_equivalent.py` (create) — deterministic grounded extractor; writes `un_equivalent` to frontmatter.
- `scripts/infer_un_equivalent.py` (create) — Batch-API inference; writes `un_equivalent_ai` to frontmatter.
- `assets/app.js` (modify) — render grounded + AI equivalents as links; AI block labelled "AI-suggested — verify against source".
- `assets/styles.css` (modify) — `.chip.ai` unverified treatment + `.meta-item.ai` block styling.
- `tests/test_un_refs.py` (create) — unit tests for the shared helpers.
- `tests/test_build.py` (modify) — tests for `un_equivalent_ai` validation, `un_index`, derived `related`.
- `tests/test_infer_un_equivalent.py` (create) — tests for prompt construction, parse/validate, frontmatter write (mocked; no network).

---

## Task 1: Shared UN-reference helpers (`scripts/un_refs.py`)

**Files:**
- Create: `scripts/un_refs.py`
- Test: `tests/test_un_refs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_un_refs.py
from scripts.un_refs import normalize_un, ece_id_to_un, scan_grounded_un

def test_normalize_un_canonicalizes_spacing_and_case():
    assert normalize_un("un r94") == "UN R94"
    assert normalize_un("UN R13H") == "UN R13H"
    assert normalize_un("R94") == "UN R94"
    assert normalize_un("UN R0") is None      # junk
    assert normalize_un("UN R94x") is None     # bad suffix
    assert normalize_un("garbage") is None

def test_ece_id_to_un_parses_ids():
    assert ece_id_to_un("ece-r94") == "UN R94"
    assert ece_id_to_un("ece-r13-h") == "UN R13H"
    assert ece_id_to_un("ece-r0") is None      # junk number
    assert ece_id_to_un("us-fmvss-208") is None

def test_scan_grounded_un_finds_only_un_ece_citations():
    body = (
        "This standard aligns with UN Regulation No. 94 and ECE R95. "
        "It references Regulation (EC) No 661/2009 which is NOT a UN reg. "
        "See also UN R0 (junk) and plain Regulation No. 12 (ambiguous)."
    )
    found = scan_grounded_un(body)
    assert found == ["UN R94", "UN R95"]   # sorted, deduped; EC/junk/ambiguous excluded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_un_refs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.un_refs'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/un_refs.py
"""Shared helpers for UN/ECE regulation cross-references.

A "UN R number" is the canonical form ``UN R<digits>[<uppercase-letter>]``
(e.g. ``UN R94``, ``UN R13H``). ECE record ids encode the same number
(``ece-r94`` -> ``UN R94``, ``ece-r13-h`` -> ``UN R13H``).
"""
from __future__ import annotations

import re

# Canonical validated form (must match build.py UN_EQUIVALENT_RE intent, but
# build.py allows a lowercase suffix; we canonicalize to uppercase here).
_CANON_RE = re.compile(r"^UN R(\d+)([A-Z]?)$")

# Parse an ECE record id: ece-r94, ece-r13-h, ece-r13-h  (optional single-letter variant)
_ECE_ID_RE = re.compile(r"^ece-r(\d+)(?:-([a-z]))?$")

# Grounded citation forms in body text. Deliberately conservative: only matches
# explicit UN / ECE / UNECE regulation references. Does NOT match "Regulation
# (EC) No ..." / "(EU)" (different numbering) or bare "Regulation No. N".
_CITATION_RE = re.compile(
    r"\b(?:UN\s+R|ECE\s+R|UNECE\s+R)\s*(\d+)\s*([A-Za-z]?)\b"
    r"|\b(?:UN|ECE|UNECE)\s+Regulation\s+No\.?\s*(\d+)\s*([A-Za-z]?)\b",
    re.IGNORECASE,
)


def normalize_un(value: str) -> str | None:
    """Canonicalize a UN R string, or return None if invalid/junk.

    Accepts ``UN R94``, ``un r94``, ``R94`` (UN prefix optional). Rejects
    number 0 (junk) and multi-letter or non-letter suffixes.
    """
    if not isinstance(value, str):
        return None
    text = value.strip().upper()
    if not text.startswith("UN R"):
        text = "UN R" + text.lstrip("R").lstrip()
    m = _CANON_RE.match(text)
    if not m:
        return None
    number, suffix = m.group(1), m.group(2)
    if int(number) < 1:
        return None
    return f"UN R{int(number)}{suffix}"


def ece_id_to_un(reg_id: str) -> str | None:
    """Map an ECE record id to its canonical UN R number, or None."""
    m = _ECE_ID_RE.match(reg_id or "")
    if not m:
        return None
    number, suffix = m.group(1), (m.group(2) or "")
    return normalize_un(f"UN R{number}{suffix.upper()}")


def scan_grounded_un(body: str) -> list[str]:
    """Return sorted, de-duplicated canonical UN R numbers cited in body text."""
    found: set[str] = set()
    for m in _CITATION_RE.finditer(body or ""):
        number = m.group(1) or m.group(3)
        suffix = (m.group(2) or m.group(4) or "")
        canon = normalize_un(f"UN R{number}{suffix.upper()}")
        if canon:
            found.add(canon)
    return sorted(found, key=lambda s: (int(re.search(r"\d+", s).group()), s))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_un_refs.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/un_refs.py tests/test_un_refs.py
git commit -m "feat(equiv): add shared UN-reference helpers (parse/normalize/scan)"
```

---

## Task 2: build.py — `un_equivalent_ai` field, `un_index`, derived `related`

**Files:**
- Modify: `scripts/build.py` (OPTIONAL_KEYS ~46, LIST_FIELDS ~73, validation ~196, `build_record` ~370, `build()` ~449-470, `write_taxonomy_json` ~321)
- Test: `tests/test_build.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_build.py  (add these)
from scripts.build import derive_related, build_un_index

def test_build_un_index_maps_un_number_to_ece_id():
    records = [
        {"id": "ece-r94", "un_equivalent": [], "un_equivalent_ai": []},
        {"id": "ece-r13-h", "un_equivalent": [], "un_equivalent_ai": []},
        {"id": "us-fmvss-208", "un_equivalent": [], "un_equivalent_ai": ["UN R94"]},
    ]
    assert build_un_index(records) == {"UN R94": "ece-r94", "UN R13H": "ece-r13-h"}

def test_derive_related_links_grounded_siblings_and_ece_record():
    records = [
        {"id": "ece-r94", "un_equivalent": [], "un_equivalent_ai": []},
        {"id": "us-fmvss-208", "un_equivalent": ["UN R94"], "un_equivalent_ai": []},
        {"id": "ca-cmvss-208", "un_equivalent": ["UN R94"], "un_equivalent_ai": []},
        {"id": "us-fmvss-101", "un_equivalent": [], "un_equivalent_ai": ["UN R94"]},
    ]
    related = derive_related(records)
    # grounded citers + the ECE record link to each other
    assert set(related["us-fmvss-208"]) == {"ece-r94", "ca-cmvss-208"}
    assert set(related["ece-r94"]) == {"us-fmvss-208", "ca-cmvss-208"}
    # AI-only link does NOT create a related edge
    assert related["us-fmvss-101"] == []

def test_derive_related_caps_fan_out_at_12():
    records = [{"id": "ece-r10", "un_equivalent": [], "un_equivalent_ai": []}]
    records += [{"id": f"reg-{i}", "un_equivalent": ["UN R10"], "un_equivalent_ai": []} for i in range(20)]
    related = derive_related(records)
    assert len(related["ece-r10"]) == 12

def test_un_equivalent_ai_validates_format():
    from scripts.build import validate_un_equivalent_ai, BuildIssue
    issues = []
    validate_un_equivalent_ai({"un_equivalent_ai": ["UN R94", "bogus"]}, issues)
    assert any("bogus" in i.message for i in issues)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_build.py -k "un_index or derive_related or un_equivalent_ai" -v`
Expected: FAIL with `ImportError: cannot import name 'derive_related'`

- [ ] **Step 3: Implement**

In `scripts/build.py`:

(a) Add to `OPTIONAL_KEYS` (after `"un_equivalent",`):
```python
    "un_equivalent_ai",
```
(b) Add to `LIST_FIELDS` (after `"un_equivalent",`):
```python
    "un_equivalent_ai",
```
(c) Import the shared helper near the top imports:
```python
from scripts.un_refs import ece_id_to_un, normalize_un
```
(Use a path-robust import: if `build.py` is run as a script, add a `try/except ImportError` falling back to `from un_refs import ...`.)

(d) Add a validator beside `validate_un_equivalent`:
```python
MAX_RELATED = 12


def validate_un_equivalent_ai(metadata: dict[str, Any], issues: list[BuildIssue]) -> None:
    for value in as_list(metadata.get("un_equivalent_ai"), "un_equivalent_ai", issues):
        if not isinstance(value, str) or not UN_EQUIVALENT_RE.match(value):
            issues.append(BuildIssue("ERROR", f"un_equivalent_ai value '{value}' must match ^UN R\\d+[a-z]?$"))
```

(e) Call it in `build_record` after `validate_un_equivalent(metadata, issues)`:
```python
    validate_un_equivalent_ai(metadata, issues)
```

(f) In `build_record`'s record dict, add the AI field and STOP reading `related` from frontmatter (it is derived later). Replace the `"related": ...` line with:
```python
        "un_equivalent_ai": as_list(metadata.get("un_equivalent_ai"), "un_equivalent_ai", []),
        "related": [],  # derived after all records load (see derive_related)
```

(g) Add the index + derivation functions (place above `build()`):
```python
def build_un_index(records: list[dict[str, Any]]) -> dict[str, str]:
    """Map each canonical UN R number to the ECE record id that represents it."""
    index: dict[str, str] = {}
    for record in records:
        un = ece_id_to_un(record.get("id", ""))
        if un:
            index[un] = record["id"]
    return index


def derive_related(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Derive related-record edges from GROUNDED shared-UN clusters only.

    A record belongs to UN-number cluster K if K is in its grounded
    ``un_equivalent`` OR it is the ECE record for K. Records sharing a cluster
    are related. AI-inferred equivalents never create related edges. Fan-out is
    capped at MAX_RELATED, with the ECE record preferred.
    """
    members: dict[str, list[str]] = {}
    keys_by_record: dict[str, set[str]] = {}
    for record in records:
        rid = record.get("id")
        if not rid:
            continue
        keys: set[str] = set()
        own = ece_id_to_un(rid)
        if own:
            keys.add(own)
        for value in record.get("un_equivalent", []):
            canon = normalize_un(value)
            if canon:
                keys.add(canon)
        keys_by_record[rid] = keys
        for key in keys:
            members.setdefault(key, []).append(rid)

    related: dict[str, list[str]] = {}
    for rid, keys in keys_by_record.items():
        siblings: list[str] = []
        seen = {rid}
        # ECE records first (stable, navigable anchor), then the rest sorted.
        cluster_ids = sorted({m for key in keys for m in members.get(key, [])})
        cluster_ids.sort(key=lambda x: (ece_id_to_un(x) is None, x))
        for other in cluster_ids:
            if other in seen:
                continue
            seen.add(other)
            siblings.append(other)
            if len(siblings) >= MAX_RELATED:
                break
        related[rid] = siblings
    return related
```

(h) In `build()`, after the final `records = [...]` sort (line ~453) and before writing outputs, derive and attach `related`, and build the index:
```python
    related_map = derive_related(records)
    for record in records:
        record["related"] = related_map.get(record["id"], [])
    un_index = build_un_index(records)
```
(i) Pass `un_index` to `write_taxonomy_json` — update its signature and the call:
```python
def write_taxonomy_json(taxonomy, region_series, un_index, dist_dir):
    payload = dict(taxonomy)
    payload["region_series"] = region_series
    payload["un_index"] = un_index
    ...
```
Call site (line ~470):
```python
    write_taxonomy_json(taxonomy, region_series, un_index, DIST_DIR)
```
(j) `warn_for_missing_related` runs on frontmatter `related` today; since `related` is now derived from in-corpus ids it can never reference a missing id. Leave the function but call it AFTER derivation (move the `warn_for_missing_related(records, issues_by_id)` call to just after the derivation block). It becomes a cheap invariant check.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_build.py -v`
Expected: PASS (all, including the 4 new + existing 41)

- [ ] **Step 5: Build smoke-test**

Run: `python scripts/build.py` then confirm no ERROR lines:
```bash
python scripts/build.py
```
Expected: build completes, exit 0; `dist/data/taxonomy.json` now contains a `un_index` key (empty `{}` until ECE records exist — they do, so it should map ~80 UN numbers).

- [ ] **Step 6: Commit**

```bash
git add scripts/build.py tests/test_build.py
git commit -m "feat(equiv): derive related from grounded UN clusters; add un_equivalent_ai + un_index"
```

---

## Task 3: Reader UI — grounded + AI-suggested equivalents as links

**Files:**
- Modify: `assets/app.js` (`facetChips` ~211, `relatedLinks` ~217, `readerBodyHtml` ~249-274, data load where TAXONOMY is parsed)
- Modify: `assets/styles.css` (chip styles)

- [ ] **Step 1: Add a UN-link helper and an AI block to the reader**

In `assets/app.js`, after `TAXONOMY` is loaded, expose the index (near where `region_series` is read):
```javascript
    const UN_INDEX = (TAXONOMY && TAXONOMY.un_index) || {};
```

Add helper functions next to `relatedLinks`:
```javascript
    // Render UN R numbers as chips, linking to the ECE record when one exists.
    // `unverified` adds the AI treatment (dashed, tinted).
    function unChips(label, values, unverified) {
      if (!values || values.length === 0) return "";
      const cls = unverified ? "chip ai" : "chip";
      const chips = values.map((un) => {
        const targetId = UN_INDEX[un];
        if (targetId && recordById.has(targetId)) {
          return `<a class="${cls}" href="#reg-${slug(targetId)}" title="${escapeHtml(unverified ? "AI-suggested — verify against source" : un)}">${escapeHtml(un)}</a>`;
        }
        return `<span class="${cls}">${escapeHtml(un)}</span>`;
      }).join("");
      const note = unverified
        ? `<span class="ai-note">AI-suggested — verify against source</span>`
        : "";
      return `<div class="meta-item${unverified ? " ai" : ""}"><strong>${escapeHtml(label)}</strong>${note}<div class="chips">${chips}</div></div>`;
    }
```

Replace the two equivalents lines in `readerBodyHtml` (currently `${facetChips("UN Equivalent", record.un_equivalent)}`) with:
```javascript
                ${unChips("UN Equivalent", record.un_equivalent, false)}
                ${unChips("AI-Suggested Equivalent", record.un_equivalent_ai, true)}
                ${relatedLinks(record.related)}
```

- [ ] **Step 2: Add styles**

In `assets/styles.css`, add:
```css
.chip.ai {
  border: 1px dashed var(--honda-red, #cc0000);
  background: color-mix(in srgb, var(--honda-red, #cc0000) 8%, transparent);
  color: inherit;
}
.meta-item.ai .ai-note {
  display: block;
  font-size: 0.75rem;
  font-style: italic;
  opacity: 0.75;
  margin: 0.15rem 0 0.25rem;
}
a.chip.ai:hover { text-decoration: underline; }
```

- [ ] **Step 3: Manually seed ONE record and verify the grounded render path in the browser**

Temporarily add to `regulations/ca-mvsr-c-r-c---c--1038-s208.md` frontmatter (a non-ECE record): `un_equivalent: ["UN R94"]`. Rebuild:
```bash
python scripts/build.py
```
Serve `dist/` and open the seeded record in the reader. Verify in the browser (Playwright or manual in Edge):
- (a) the grounded "UN Equivalent: UN R94" chip renders and **links** to `ece-r94`;
- (b) clicking it navigates to the ECE R94 record;
- (c) a "Related" link back to the grounded record appears on ece-r94.

Then REMOVE the temporary seed and rebuild (the real grounded values come from Task 2's extractor run, not hand-edits).

- [ ] **Step 4: Commit**

```bash
git add assets/app.js assets/styles.css
git commit -m "feat(equiv): render grounded + AI-suggested UN equivalents as links in reader"
```

---

## Task 4: Grounded extractor (`scripts/extract_un_equivalent.py`)

**Files:**
- Create: `scripts/extract_un_equivalent.py`
- Test: `tests/test_un_refs.py` (extend) — extractor logic is thin; cover the write path

- [ ] **Step 1: Write the failing test**

```python
# tests/test_un_refs.py  (add)
def test_extract_writes_grounded_for_non_ece(tmp_path):
    import frontmatter
    from scripts.extract_un_equivalent import extract_for_record
    p = tmp_path / "us-fmvss-301.md"
    p.write_text(
        "---\nid: us-fmvss-301\nregion: US\ntitle: Fuel\n---\n"
        "Harmonized with UN Regulation No. 34 on fuel tanks.\n",
        encoding="utf-8",
    )
    changed = extract_for_record(p)
    assert changed is True
    assert frontmatter.load(p)["un_equivalent"] == ["UN R34"]

def test_extract_skips_ece_self_reference(tmp_path):
    import frontmatter
    from scripts.extract_un_equivalent import extract_for_record
    p = tmp_path / "ece-r94.md"
    p.write_text(
        "---\nid: ece-r94\nregion: ECE\ntitle: Frontal collision\n---\n"
        "This is UN Regulation No. 94 itself.\n",
        encoding="utf-8",
    )
    changed = extract_for_record(p)
    # ECE records get no self-referential un_equivalent
    assert frontmatter.load(p).get("un_equivalent", []) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_un_refs.py -k extract -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.extract_un_equivalent'`

- [ ] **Step 3: Implement**

```python
# scripts/extract_un_equivalent.py
"""Deterministically extract grounded UN R citations from regulation bodies.

For every non-ECE record, scan the body text for explicit UN/ECE regulation
citations and write the canonical UN R numbers to the ``un_equivalent``
frontmatter field. ECE records are skipped (their UN number is their identity,
so a self-reference would be meaningless). No network calls.

Usage:
    python scripts/extract_un_equivalent.py            # all records
    python scripts/extract_un_equivalent.py --dry-run  # report, write nothing
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"

try:
    from scripts.un_refs import ece_id_to_un, scan_grounded_un
except ImportError:
    from un_refs import ece_id_to_un, scan_grounded_un


def extract_for_record(path: Path, dry_run: bool = False) -> bool:
    """Write grounded un_equivalent for one record. Returns True if changed."""
    post = frontmatter.load(path)
    rid = post.get("id", path.stem)
    if ece_id_to_un(rid):           # ECE record — skip self-reference
        return False
    found = scan_grounded_un(post.content or "")
    current = list(post.get("un_equivalent", []) or [])
    if found == current:
        return False
    if not dry_run:
        post["un_equivalent"] = found
        path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract grounded UN equivalents.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    changed = 0
    for path in sorted(REGULATIONS_DIR.glob("*.md")):
        if extract_for_record(path, args.dry_run):
            changed += 1
            print(f"  {'[dry] ' if args.dry_run else ''}{path.stem}: {frontmatter.load(path).get('un_equivalent', [])}")
    print(f"\n{changed} record(s) {'would change' if args.dry_run else 'updated'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_un_refs.py -v`
Expected: PASS (all)

- [ ] **Step 5: Dry-run on the real corpus, then apply**

```bash
python scripts/extract_un_equivalent.py --dry-run
```
Eyeball the output for false positives (EC/EU regs, ambiguous matches). If clean, apply:
```bash
python scripts/extract_un_equivalent.py
python scripts/build.py   # confirm no ERRORs; related edges now populate
```

- [ ] **Step 6: Commit**

```bash
git add scripts/extract_un_equivalent.py tests/test_un_refs.py regulations
git commit -m "feat(equiv): extract grounded UN equivalents from regulation text"
```
(Use explicit paths — never `git add -A`/`.`)

---

## Task 5: AI inference (`scripts/infer_un_equivalent.py`, Batch API)

**Files:**
- Create: `scripts/infer_un_equivalent.py`
- Test: `tests/test_infer_un_equivalent.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_infer_un_equivalent.py
from scripts.infer_un_equivalent import build_prompt, parse_ai_equiv

VALID = {"UN R94": "ece-r94", "UN R95": "ece-r95", "UN R34": "ece-r34"}

def test_prompt_lists_valid_targets_and_allows_none():
    reg = {"id": "us-fmvss-208", "title": "Occupant crash protection", "region": "US", "citation": "49 CFR 571.208", "body": "frontal..."}
    prompt = build_prompt(reg, VALID)
    assert "UN R94" in prompt
    assert "none" in prompt.lower() or "empty" in prompt.lower()

def test_parse_keeps_only_valid_corpus_numbers():
    out = parse_ai_equiv('{"un_equivalent_ai": ["UN R94", "UN R999"]}', VALID, grounded=[])
    assert out == ["UN R94"]            # R999 not in corpus -> dropped

def test_parse_excludes_grounded_values():
    out = parse_ai_equiv('{"un_equivalent_ai": ["UN R94", "UN R95"]}', VALID, grounded=["UN R94"])
    assert out == ["UN R95"]            # already grounded -> not duplicated into AI

def test_parse_caps_at_two():
    out = parse_ai_equiv('{"un_equivalent_ai": ["UN R94","UN R95","UN R34"]}', VALID, grounded=[])
    assert len(out) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_infer_un_equivalent.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# scripts/infer_un_equivalent.py
"""Infer cross-market UN equivalents with the Anthropic Batch API (Haiku).

For each non-ECE record, ask which UN R number(s) it is the cross-market
equivalent of, constrained to the UN regulations actually present in the
corpus. Results are written to the SEPARATE ``un_equivalent_ai`` frontmatter
field (never commingled with grounded ``un_equivalent``) and surfaced in the
reader as "AI-suggested — verify against source".

Usage mirrors auto_tag.py:
    python scripts/infer_un_equivalent.py
    python scripts/infer_un_equivalent.py --dry-run
    python scripts/infer_un_equivalent.py --poll msgbatch_xxx
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"

try:
    from scripts.un_refs import ece_id_to_un, normalize_un
    from scripts.auto_tag import custom_id_for     # reuse the 64-char-safe mapper
except ImportError:
    from un_refs import ece_id_to_un, normalize_un
    from auto_tag import custom_id_for

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 256
BODY_TRUNCATE = 4000
POLL_INTERVAL = 30
MAX_AI = 2


def build_valid_targets() -> dict[str, str]:
    """Canonical UN R number -> ECE record id, for every ECE record."""
    targets: dict[str, str] = {}
    for path in sorted(REGULATIONS_DIR.glob("*.md")):
        un = ece_id_to_un(path.stem)
        if un:
            post = frontmatter.load(path)
            targets[un] = str(post.get("title", path.stem))
    return targets


def load_candidates() -> list[dict]:
    """Non-ECE records that should be checked for an AI equivalent."""
    out = []
    for path in sorted(REGULATIONS_DIR.glob("*.md")):
        if ece_id_to_un(path.stem):
            continue
        post = frontmatter.load(path)
        body = (post.content or "")[:BODY_TRUNCATE]
        out.append({
            "id": post.get("id", path.stem),
            "path": str(path),
            "region": post.get("region", ""),
            "citation": post.get("citation", ""),
            "title": post.get("title", ""),
            "body": body,
            "grounded": list(post.get("un_equivalent", []) or []),
        })
    return out


def build_prompt(reg: dict, valid_targets: dict[str, str]) -> str:
    catalog = "\n".join(f"  - {un}: {title}" for un, title in sorted(valid_targets.items()))
    return f"""\
You map an automotive regulation to its cross-market UN (ECE) equivalent.
Return ONLY a JSON object — no prose, no markdown fences.

## Regulation
Title: {reg["title"]}
Citation: {reg["citation"]}
Region: {reg["region"]}

## Content (truncated)
{reg["body"]}

## Task
From the catalog below, pick the UN regulation(s) this regulation is the
cross-market equivalent of (covers the same subject / test). MOST regulations
have NO UN equivalent — returning an empty list is expected and correct. Do not
guess. Return at most {MAX_AI} of the strongest matches, only if confident.

## Valid UN regulations (choose ONLY from these exact strings)
{catalog}

## Required output (JSON only)
{{"un_equivalent_ai": ["UN R##", ...]}}"""


def parse_ai_equiv(text: str, valid_targets: dict[str, str], grounded: list[str]) -> list[str]:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    raw = data.get("un_equivalent_ai", [])
    if not isinstance(raw, list):
        return []
    grounded_canon = {normalize_un(g) for g in grounded}
    out: list[str] = []
    for value in raw:
        canon = normalize_un(value) if isinstance(value, str) else None
        if canon and canon in valid_targets and canon not in grounded_canon and canon not in out:
            out.append(canon)
        if len(out) >= MAX_AI:
            break
    return out


def write_ai_to_file(path: str, values: list[str]) -> None:
    p = Path(path)
    post = frontmatter.load(p)
    if values:
        post["un_equivalent_ai"] = values
    elif "un_equivalent_ai" in post:
        del post["un_equivalent_ai"]
    p.write_text(frontmatter.dumps(post), encoding="utf-8")


# run_batch / poll_and_import mirror auto_tag.py (same client, custom_id_for,
# POLL_INTERVAL loop). Build requests with build_prompt; on import, look up the
# candidate by custom_id_for(id), parse_ai_equiv(text, targets, grounded),
# write_ai_to_file. See auto_tag.py for the exact batch scaffolding to copy.
```
Copy the `run_batch`, `poll_and_import`, and `main` scaffolding from `auto_tag.py` verbatim, substituting: the request builder uses `build_prompt(reg, valid_targets)`; the importer uses `parse_ai_equiv(...)` + `write_ai_to_file(...)`; `path_by_cid` / `grounded_by_cid` are keyed by `custom_id_for(reg["id"])`. NEVER print the API key.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_infer_un_equivalent.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Dry-run, then submit the batch**

```bash
$env:ANTHROPIC_API_KEY = [Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY','User')
python scripts/infer_un_equivalent.py --dry-run    # inspect a few prompts
python scripts/infer_un_equivalent.py              # submit + poll + import
```

- [ ] **Step 6: Build + verify the AI render path in the browser**

```bash
python scripts/build.py
```
Confirm no ERRORs. Open **FMVSS 208** in the reader and verify the three render paths:
- (a) a grounded chip renders + links on a non-ECE record that cites a UN reg;
- (b) FMVSS 208 shows an **"AI-Suggested Equivalent: UN R94"** chip that is **labelled** "AI-suggested — verify against source" AND is a **clickable link** to ece-r94;
- (c) a `related` link actually navigates.
(If FMVSS 208 did not get UN R94 from the model, note it and spot-check whichever records did receive AI suggestions; the render contract is what's under test.)

- [ ] **Step 7: Commit**

```bash
git add scripts/infer_un_equivalent.py tests/test_infer_un_equivalent.py regulations
git commit -m "feat(equiv): infer cross-market UN equivalents via Batch API (AI-suggested)"
```

---

## Self-Review Checklist (run after implementation)

- **Spec coverage:** grounded field ✓ (Task 4), AI field ✓ (Task 5), derived related ✓ (Task 2), un_index ✓ (Task 2), reader links incl. AI-clickable ✓ (Task 3), three browser-verified render paths ✓ (Tasks 3 & 5).
- **Provenance never commingled:** `un_equivalent` (grounded) and `un_equivalent_ai` (AI) are separate fields, separate reader blocks, and AI is excluded from `related`.
- **No false-positive pressure:** prompt makes empty first-class, caps at 2, constrains to corpus.
- **Type consistency:** `custom_id_for` reused from auto_tag.py; `normalize_un`/`ece_id_to_un` are the single source of UN-number logic across build/extract/infer.
