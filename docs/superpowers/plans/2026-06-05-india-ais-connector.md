# India/AIS Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the 3 India `in-*` regulation stubs' source links (`morth.nic.in` → `morth.gov.in`) and give them a consistent CMVR/AIS framework body, preserving the LLM tags and `un_equivalent`/`un_equivalent_ai` from API-2.

**Architecture:** A new **network-free** `connectors/india.py` (shaped like `connectors/gulf.py`) driven by a new `manifests/in.yaml`, registered in `scripts/pull.py`. It is a deterministic transform: per record, canonicalize the URL, set `source_api: ais`, write a framework body, and re-pass the existing tags/cross-references through `write_md`.

**Tech Stack:** Python 3.14, `python-frontmatter`, PyYAML, pytest (pure unit tests, no network, no fixtures).

**Spec:** `docs/superpowers/specs/2026-06-05-india-ais-connector-design.md`

---

## File Structure

- `manifests/in.yaml` (create) — `records:` list of `{id, citation, source_url}` for the 3 `in-*` stubs.
- `connectors/india.py` (create) — `canonical_url`, `build_body`, `_load_existing`, `pull`.
- `scripts/pull.py` (modify) — register `"IN"` in `REGION_CONNECTOR`.
- `tests/test_india.py` (create) — pure unit + integration tests.

**Verified facts:** `IN` is already in the allowed-region set in `connectors/_common.py`. `write_md` already preserves `commodities/systems/vehicle_categories/tagging_status/tagged_at`. The 3 stub ids are `in-ais-038-rev-2-ais-156`, `in-bs-vi-india-cafe-fuel-consumption`, `in-central-motor-vehicles-rules-cmvr-ais-type-approval-framework`.

---

## Task 1: Manifest + connector + registration (with unit + integration tests)

**Files:**
- Create: `manifests/in.yaml`, `connectors/india.py`, `tests/test_india.py`
- Modify: `scripts/pull.py`

- [ ] **Step 1: Generate `manifests/in.yaml` from the existing stubs**

Run from repo root (do NOT commit the snippet, only its output):
```python
import frontmatter, glob, os, yaml
records = []
for p in sorted(glob.glob("regulations/in-*.md")):
    post = frontmatter.load(p)
    records.append({
        "id": os.path.basename(p)[:-3],
        "citation": str(post.get("citation", "")).strip(),
        "source_url": str(post.get("source_url", "")).strip(),
    })
with open("manifests/in.yaml", "w", encoding="utf-8") as fh:
    yaml.safe_dump({"region": "IN", "records": records}, fh, allow_unicode=True, sort_keys=False)
print(len(records), "entries")
```
Expected: `3 entries`.

- [ ] **Step 2: Write the failing tests at `tests/test_india.py`**

```python
import frontmatter
from connectors.india import canonical_url, build_body, pull

def test_canonical_url_rewrites_morth_domain():
    assert canonical_url("https://morth.nic.in/sites/default/files/ASI/AIS-156.pdf") == \
        "https://morth.gov.in/sites/default/files/ASI/AIS-156.pdf"
    assert canonical_url("https://morth.nic.in") == "https://morth.gov.in"
    # non-morth hosts unchanged
    assert canonical_url("https://www.araiindia.com/certification") == \
        "https://www.araiindia.com/certification"
    assert canonical_url("") == ""

def test_build_body_has_citation_framework_note_and_link():
    body = build_body("AIS-156", "EV battery safety", "https://morth.gov.in/x")
    assert "AIS-156" in body
    assert "EV battery safety" in body
    assert "CMVR" in body and "AIS" in body
    assert "https://morth.gov.in/x" in body

def _manifest(tmp_path, entry):
    import yaml
    mp = tmp_path / "in.yaml"
    mp.write_text(yaml.safe_dump({"region": "IN", "records": [entry]}, allow_unicode=True), encoding="utf-8")
    return mp

def test_pull_repoints_and_preserves(tmp_path):
    dest = tmp_path / "regs"; dest.mkdir()
    existing = frontmatter.Post(
        "old body", id="in-ais-038-rev-2-ais-156", title="EV battery safety", region="IN",
        citation="AIS-038 Rev.2 / AIS-156", status="in-force",
        source_url="https://morth.nic.in/sites/default/files/ASI/AIS-156.pdf",
        source_api="spreadsheet", tagging_status="llm-tagged", commodities=["Battery"],
        paywall=True, un_equivalent=["UN R100"], un_equivalent_ai=["UN R10"],
    )
    (dest / "in-ais-038-rev-2-ais-156.md").write_text(frontmatter.dumps(existing), encoding="utf-8")

    manifest = _manifest(tmp_path, {
        "id": "in-ais-038-rev-2-ais-156", "citation": "AIS-038 Rev.2 / AIS-156",
        "source_url": "https://morth.nic.in/sites/default/files/ASI/AIS-156.pdf",
    })
    pull(manifest, dest)

    post = frontmatter.load(dest / "in-ais-038-rev-2-ais-156.md")
    assert post["source_api"] == "ais"
    assert post["source_url"] == "https://morth.gov.in/sites/default/files/ASI/AIS-156.pdf"
    assert post["commodities"] == ["Battery"]            # preserved by write_md
    assert post["tagging_status"] == "llm-tagged"
    assert post["paywall"] is True
    assert post["un_equivalent"] == ["UN R100"]
    assert post["un_equivalent_ai"] == ["UN R10"]
    assert post["title"] == "EV battery safety"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_india.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'connectors.india'`

- [ ] **Step 4: Implement `connectors/india.py`**

```python
"""India/AIS connector — thin, network-free link refresh + framework body.

The 3 India records are framework aggregates (AIS standards under the CMVR,
administered by ARAI/MoRTH). The Ministry migrated morth.nic.in -> morth.gov.in;
this connector canonicalizes the stale domain, writes a CMVR/AIS framework body,
and preserves the LLM tags and UN cross-references from API-2. No network calls
(morth.gov.in is slow/timeout-prone; the domain rewrite is a strict improvement
over the redirecting morth.nic.in link regardless).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

import frontmatter
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import write_md


def canonical_url(url: str) -> str:
    """Rewrite the migrated ministry domain; leave other hosts unchanged."""
    return (url or "").replace("morth.nic.in", "morth.gov.in")


def build_body(citation: str, title: str | None, url: str) -> str:
    head = f"{citation} — {title}" if title else citation
    return "\n".join([
        f"# {head}",
        "",
        f"**Citation:** {citation}",
        "",
        "India vehicle type approval is governed by the **Central Motor Vehicles Rules "
        "(CMVR)**; technical requirements are set by **Automotive Industry Standards "
        "(AIS)**, administered by ARAI for the Ministry of Road Transport & Highways "
        "(MoRTH). Many AIS standards are aligned with UN/ECE Regulations.",
        "",
        f"[Official source]({url})",
    ])


def _load_existing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return dict(frontmatter.load(path).metadata)


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}

    pulled: list[Path] = []
    failed: list[str] = []
    for entry in manifest.get("records", []):
        file_id = str(entry.get("id", "")).strip()
        citation = str(entry.get("citation", "")).strip()
        manifest_url = str(entry.get("source_url", "")).strip()
        if not file_id or not citation:
            continue

        existing = _load_existing(dest_dir / f"{file_id}.md")
        print(f"  Enriching IN {citation} ...", end=" ", flush=True)
        try:
            url = canonical_url(existing.get("source_url") or manifest_url)
            title = existing.get("title") or citation
            body = build_body(citation, existing.get("title"), url)

            record: dict[str, Any] = {
                "id": file_id, "title": title, "region": "IN", "citation": citation,
                "status": existing.get("status") or "in-force",
                "source_url": url, "source_api": "ais",
                "tagging_status": existing.get("tagging_status", "untagged"),
            }
            for field in ("un_equivalent", "un_equivalent_ai", "aliases",
                          "translation_status", "paywall", "tagged_at"):
                if existing.get(field) not in (None, [], ""):
                    record[field] = existing[field]

            pulled.append(write_md(record, body, dest_dir))
            print("OK")
        except Exception as exc:
            failed.append(f"{citation}: {exc}")
            print(f"FAILED: {exc}")

    if failed:
        print(f"\n{len(failed)} failure(s):")
        for msg in failed:
            print(f"  {msg}")
    return pulled
```

- [ ] **Step 5: Register the connector in `scripts/pull.py`**

In `REGION_CONNECTOR` (after the `"GCC"` line) add:
```python
    "IN": ("connectors.india", "manifests/in.yaml"),
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_india.py -v` → all PASS. Then full suite `python -m pytest -q` → all PASS.

- [ ] **Step 7: Commit (explicit paths; never git add -A / .)**

```bash
git add manifests/in.yaml connectors/india.py scripts/pull.py tests/test_india.py
git commit -m "feat(in): India/AIS connector (network-free link refresh + framework body)"
```

---

## Task 2: Live run + build verification

**Files:**
- Modify: `regulations/in-*.md` (regenerated by the connector)

- [ ] **Step 1: Run the connector**

Run: `python scripts/pull.py --region IN`
Expected: 3 `OK` lines, no traceback, `3 record(s)` written.

- [ ] **Step 2: Spot-check repoint + preservation**

```bash
python -c "import frontmatter; p=frontmatter.load('regulations/in-ais-038-rev-2-ais-156.md'); print('api:',p.get('source_api')); print('url:',p.get('source_url')); print('un:',p.get('un_equivalent'),'tags:',p.get('commodities'))"
```
Expected: `api: ais`; `url` uses `morth.gov.in`; `un` present (`['UN R100']`); `commodities` preserved.

- [ ] **Step 3: Confirm no cross-references dropped (write `_incheck.py`, run, delete)**

```python
import frontmatter, glob, subprocess
from pathlib import Path
def main_meta(rel):
    blob = subprocess.run(["git", "show", f"main:{rel}"], capture_output=True, text=True).stdout
    return frontmatter.loads(blob).metadata if blob else {}
drops = []
for p in glob.glob("regulations/in-*.md"):
    now = frontmatter.load(p).metadata; old = main_meta(Path(p).as_posix())
    for f in ("un_equivalent", "un_equivalent_ai"):
        lost = set(old.get(f) or []) - set(now.get(f) or [])
        if lost: drops.append((Path(p).name, f, sorted(lost)))
print("DROPS:", drops or "none")
```
Expected: `DROPS: none`. (Delete `_incheck.py` after.)

- [ ] **Step 4: Build and confirm no regressions**

Run: `python scripts/build.py` then `python -m pytest -q`
Expected: `Build complete: 728 records, 0 errors, 0 warnings`; all tests pass.

- [ ] **Step 5: Commit the regenerated records**

```bash
git add regulations
git commit -m "data(in): refresh 3 India records (morth.gov.in links + AIS framework body)"
```

---

## Self-Review Checklist (run after implementation)

- **Spec coverage:** manifest+connector+registration (Task 1) ✓; `canonical_url` domain rewrite (Task 1) ✓; framework body (Task 1) ✓; `source_api=ais` + preserve tags/equivalents/title/status/paywall (Task 1) ✓; network-free (no session imported/constructed) ✓; cross-reference drop check (Task 2) ✓.
- **Type consistency:** `canonical_url(url)->str`; `build_body(citation, title, url)->str`; `pull(manifest_path, dest_dir)->list[Path]` — consistent.
- **Safety:** explicit `git add` paths; no `git add -A`.
