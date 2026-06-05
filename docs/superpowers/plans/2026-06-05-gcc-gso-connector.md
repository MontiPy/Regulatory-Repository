# GCC/GSO Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the 63 GCC `gcc-*` regulation stubs a live public source link (the consolidated GSO Technical Regulations PDF) and a consistent framework-reference body, while preserving the LLM tags and `un_equivalent`/`un_equivalent_ai` from API-2.

**Architecture:** A new `connectors/gulf.py` (shaped like `connectors/china.py`) driven by a new `manifests/gcc.yaml`, registered in `scripts/pull.py`. It checks the master GSO PDF's reachability once per run, then per record repoints `source_url`, sets `source_api: gso`, writes a framework-reference body, and re-passes the existing tags/cross-references through `write_md`. No per-standard parsing.

**Tech Stack:** Python 3.14, `requests` (via `connectors._common.RateLimitedSession`), `python-frontmatter`, PyYAML, pytest with fake-session stubs (no live network, no binary fixture).

**Spec:** `docs/superpowers/specs/2026-06-05-gcc-gso-connector-design.md`

---

## File Structure

- `manifests/gcc.yaml` (create) — `records:` list of `{id, citation, source_url}`, one per existing `gcc-*` stub (63).
- `connectors/gulf.py` (create) — `MASTER_URL`, `master_pdf_live`, `build_body`, `_load_existing`, `pull`.
- `scripts/pull.py` (modify) — register `"GCC"` in `REGION_CONNECTOR`.
- `tests/test_gulf.py` (create) — fake-session unit + integration tests.

**Verified facts:** `MASTER_URL` = `https://static.gso.org.sa/gso-public-docs/conformity/mutabiq/GSO_TechnicalRegulations_MV_2027_MY-D2.pdf` returns `200 application/pdf`. `GCC` is already in the allowed-region set in `connectors/_common.py`. `write_md` already preserves `commodities/systems/vehicle_categories/tagging_status/tagged_at`.

---

## Task 1: Manifest + connector skeleton with `master_pdf_live`

**Files:**
- Create: `manifests/gcc.yaml`
- Create: `connectors/gulf.py`
- Test: `tests/test_gulf.py`

- [ ] **Step 1: Generate `manifests/gcc.yaml` from the existing stubs**

Run this one-off generator from the repo root (do NOT commit the snippet — only its output):

```python
import frontmatter, glob, os, yaml
records = []
for p in sorted(glob.glob("regulations/gcc-*.md")):
    post = frontmatter.load(p)
    records.append({
        "id": os.path.basename(p)[:-3],
        "citation": str(post.get("citation", "")).strip(),
        "source_url": str(post.get("source_url", "")).strip(),
    })
with open("manifests/gcc.yaml", "w", encoding="utf-8") as fh:
    yaml.safe_dump({"region": "GCC", "records": records}, fh, allow_unicode=True, sort_keys=False)
print(len(records), "entries")
```
Expected: `63 entries`; `manifests/gcc.yaml` starts with `region: GCC` then a `records:` list.

- [ ] **Step 2: Write the failing test at `tests/test_gulf.py`**

```python
from connectors.gulf import master_pdf_live, MASTER_URL

class FakeResp:
    def __init__(self, ct="application/pdf", status=200):
        self.headers = {"Content-Type": ct}; self.status_code = status; self.encoding = "utf-8"
    def raise_for_status(self): pass

class FakeSession:
    def __init__(self, resp=None, raises=False):
        self._resp = resp or FakeResp(); self._raises = raises; self.urls = []
    def get(self, url, **kw):
        self.urls.append(url)
        if self._raises:
            raise RuntimeError("boom")
        return self._resp
    def close(self): pass

def test_master_pdf_live_true_for_pdf_200():
    assert master_pdf_live(FakeSession(FakeResp("application/pdf", 200))) is True

def test_master_pdf_live_false_for_404():
    assert master_pdf_live(FakeSession(FakeResp("text/html", 404))) is False

def test_master_pdf_live_false_on_exception():
    assert master_pdf_live(FakeSession(raises=True)) is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_gulf.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'connectors.gulf'`

- [ ] **Step 4: Implement the skeleton + `master_pdf_live`**

```python
# connectors/gulf.py
"""GCC/GSO connector — link + framework-reference enrichment.

GCC member states adopt UN/ECE regulations; individual GSO standards are sold,
so full text is not captured. This connector gives each gcc-* record a live
public source link (the consolidated GSO Technical Regulations PDF) and a
framework-reference body, preserving the LLM tags and UN cross-references built
in API-2. No per-standard parsing (the master PDF's table is column-wise and
unreliable to reconstruct).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

import frontmatter
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, write_md

MASTER_URL = (
    "https://static.gso.org.sa/gso-public-docs/conformity/mutabiq/"
    "GSO_TechnicalRegulations_MV_2027_MY-D2.pdf"
)


def master_pdf_live(session: Any) -> bool:
    """True iff the consolidated GSO PDF responds 200 with a PDF content type."""
    try:
        resp = session.get(MASTER_URL, stream=True)
    except Exception:
        return False
    if getattr(resp, "status_code", 200) != 200:
        return False
    return "pdf" in resp.headers.get("Content-Type", "").lower()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_gulf.py -v`
Expected: PASS (3 tests). Then full suite `python -m pytest -q` → all PASS.

- [ ] **Step 6: Commit (explicit paths; never git add -A / .)**

```bash
git add manifests/gcc.yaml connectors/gulf.py tests/test_gulf.py
git commit -m "feat(gcc): GCC/GSO connector skeleton + manifest + master-PDF reachability check"
```

---

## Task 2: `build_body`

**Files:**
- Modify: `connectors/gulf.py`
- Test: `tests/test_gulf.py`

- [ ] **Step 1: Append the failing tests**

```python
from connectors.gulf import build_body

def test_build_body_links_master_when_reachable():
    body = build_body("GSO 1053:2002", "Brake hoses", MASTER_URL, reachable=True)
    assert "GSO 1053:2002" in body
    assert "Brake hoses" in body
    assert MASTER_URL in body
    assert "sold" in body.lower()

def test_build_body_notes_unavailable_when_unreachable():
    body = build_body("GSO 1053:2002", "Brake hoses", "https://fallback.example/x", reachable=False)
    assert "GSO 1053:2002" in body
    assert "https://fallback.example/x" in body
    assert "could not be reached" in body.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_gulf.py -k build_body -v`
Expected: FAIL with `ImportError: cannot import name 'build_body'`

- [ ] **Step 3: Implement (add to `connectors/gulf.py`)**

```python
def build_body(citation: str, title: str | None, url: str, reachable: bool) -> str:
    head = f"{citation} — {title}" if title else citation
    lines = [f"# {head}", "", f"**Citation:** {citation}", ""]
    if reachable:
        lines += [
            "This Gulf (GSO) standard is part of the **GCC Technical Regulation for Motor "
            "Vehicles**. Individual GSO standards are published and sold by the GCC "
            "Standardization Organization; their full text is not freely available. The "
            "consolidated list of GSO motor-vehicle technical regulations (number, model "
            "year, subject) is published by GSO:",
            "",
            f"[GSO Technical Regulations for Motor Vehicles (consolidated list)]({url})",
        ]
    else:
        lines += [
            "This Gulf (GSO) standard is part of the GCC Technical Regulation for Motor "
            "Vehicles. Individual GSO standards are sold by the GCC Standardization "
            "Organization. The consolidated GSO regulation list could not be reached "
            "automatically at build time; see the source link for the official record.",
            "",
            f"[Official source]({url})",
        ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_gulf.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add connectors/gulf.py tests/test_gulf.py
git commit -m "feat(gcc): framework-reference body (reachable + unreachable variants)"
```

---

## Task 3: `pull()` with frontmatter-preserving merge + register in pull.py

**Files:**
- Modify: `connectors/gulf.py`
- Modify: `scripts/pull.py` (`REGION_CONNECTOR`)
- Test: `tests/test_gulf.py`

- [ ] **Step 1: Append the failing integration test**

```python
import frontmatter
from connectors.gulf import pull

def _manifest(tmp_path, entry):
    import yaml
    mp = tmp_path / "gcc.yaml"
    mp.write_text(yaml.safe_dump({"region": "GCC", "records": [entry]}, allow_unicode=True), encoding="utf-8")
    return mp

def test_pull_repoints_url_and_preserves_tags_equivalents(tmp_path, monkeypatch):
    dest = tmp_path / "regs"; dest.mkdir()
    existing = frontmatter.Post(
        "old stub body",
        id="gcc-gso-1053-2002", title="Brake hoses", region="GCC",
        citation="GSO 1053:2002", status="in-force",
        source_url="https://www.gso.org.sa/wp-content/dead.pdf", source_api="spreadsheet",
        tagging_status="llm-tagged", commodities=["Brakes"], paywall=True,
        un_equivalent=["UN R90"], un_equivalent_ai=["UN R13"],
    )
    (dest / "gcc-gso-1053-2002.md").write_text(frontmatter.dumps(existing), encoding="utf-8")

    import connectors.gulf as gulf
    monkeypatch.setattr(gulf, "RateLimitedSession", lambda **kw: FakeSession(FakeResp("application/pdf", 200)))

    manifest = _manifest(tmp_path, {
        "id": "gcc-gso-1053-2002", "citation": "GSO 1053:2002",
        "source_url": "https://www.gso.org.sa/wp-content/dead.pdf",
    })
    pull(manifest, dest)

    post = frontmatter.load(dest / "gcc-gso-1053-2002.md")
    assert post["source_api"] == "gso"
    assert post["source_url"] == gulf.MASTER_URL          # repointed to live master PDF
    assert post["commodities"] == ["Brakes"]              # tag preserved by write_md
    assert post["tagging_status"] == "llm-tagged"
    assert post["paywall"] is True                        # preserved
    assert post["un_equivalent"] == ["UN R90"]            # preserved
    assert post["un_equivalent_ai"] == ["UN R13"]         # preserved
    assert post["title"] == "Brake hoses"                 # preserved (no parsing)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gulf.py -k pull -v`
Expected: FAIL with `ImportError: cannot import name 'pull'`

- [ ] **Step 3: Implement `_load_existing` + `pull` (add to `connectors/gulf.py`)**

```python
def _load_existing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return dict(frontmatter.load(path).metadata)


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}

    session = RateLimitedSession(rate=0.5)
    reachable = master_pdf_live(session)
    print(f"  GSO master PDF reachable: {reachable}")

    pulled: list[Path] = []
    failed: list[str] = []
    for entry in manifest.get("records", []):
        file_id = str(entry.get("id", "")).strip()
        citation = str(entry.get("citation", "")).strip()
        fallback_url = str(entry.get("source_url", "")).strip()
        if not file_id or not citation:
            continue

        existing = _load_existing(dest_dir / f"{file_id}.md")
        print(f"  Enriching GCC {citation} ...", end=" ", flush=True)
        try:
            url = MASTER_URL if reachable else (fallback_url or existing.get("source_url") or MASTER_URL)
            title = existing.get("title") or citation
            body = build_body(citation, existing.get("title"), url, reachable)

            record: dict[str, Any] = {
                "id": file_id, "title": title, "region": "GCC", "citation": citation,
                "status": existing.get("status") or "in-force",
                "source_url": url, "source_api": "gso",
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

    session.close()
    if failed:
        print(f"\n{len(failed)} failure(s):")
        for msg in failed:
            print(f"  {msg}")
    return pulled
```

- [ ] **Step 4: Register the connector in `scripts/pull.py`**

In `REGION_CONNECTOR` (after the `"CN"` line) add:
```python
    "GCC": ("connectors.gulf", "manifests/gcc.yaml"),
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_gulf.py -v` → all PASS. Then full suite `python -m pytest -q` → all PASS.

- [ ] **Step 6: Commit**

```bash
git add connectors/gulf.py scripts/pull.py tests/test_gulf.py
git commit -m "feat(gcc): pull() with frontmatter-preserving merge; register GCC connector"
```

---

## Task 4: Live pull + build verification

**Files:**
- Modify: `regulations/gcc-*.md` (regenerated by the connector)

- [ ] **Step 1: Run the live connector**

Run: `python scripts/pull.py --region GCC`
Expected: a `GSO master PDF reachable: True` line, then 63 `OK` lines, no traceback. `63 record(s) written` (or similar).

- [ ] **Step 2: Spot-check link repoint + preservation**

```bash
python -c "import frontmatter; p=frontmatter.load('regulations/gcc-gso-1053-2002.md'); print('api:',p.get('source_api')); print('url:',p.get('source_url')); print('tags:',p.get('commodities')); print('un:',p.get('un_equivalent'),'ai:',p.get('un_equivalent_ai')); print('paywall:',p.get('paywall'))"
```
Expected: `api: gso`; `url` is the `static.gso.org.sa` master PDF; `commodities` non-empty (preserved); `un`/`ai` present; `paywall: True`.

- [ ] **Step 3: Confirm no cross-references dropped (write `_gcccheck.py`, run, delete)**

```python
import frontmatter, glob, subprocess
from pathlib import Path
def main_meta(rel):
    blob = subprocess.run(["git", "show", f"main:{rel}"], capture_output=True, text=True).stdout
    return frontmatter.loads(blob).metadata if blob else {}
drops = []
for p in glob.glob("regulations/gcc-*.md"):
    now = frontmatter.load(p).metadata; old = main_meta(Path(p).as_posix())
    for f in ("un_equivalent", "un_equivalent_ai"):
        lost = set(old.get(f) or []) - set(now.get(f) or [])
        if lost: drops.append((Path(p).name, f, sorted(lost)))
print("DROPS:", drops or "none")
```
Expected: `DROPS: none`. (Delete `_gcccheck.py` after.)

- [ ] **Step 4: Build and confirm no regressions**

Run: `python scripts/build.py` then `python -m pytest -q`
Expected: `Build complete: 728 records, 0 errors, 0 warnings`; all tests pass. (Record count unchanged.)

- [ ] **Step 5: Commit the regenerated records**

```bash
git add regulations
git commit -m "data(gcc): repoint 63 GCC records to live GSO master regulation + framework body"
```
Use explicit `git add regulations` — never `git add -A`/`.`.

---

## Self-Review Checklist (run after implementation)

- **Spec coverage:** manifest+connector+registration (Tasks 1,3) ✓; master-PDF reachability once per run (Task 1) ✓; repoint source_url + source_api=gso + framework body (Tasks 2,3) ✓; preserve tags + `un_equivalent`/`un_equivalent_ai` + paywall + title + status (Task 3) ✓; unreachable fallback (Tasks 2,3) ✓; no per-standard parsing ✓; cross-reference drop check (Task 4) ✓.
- **Type consistency:** `master_pdf_live(session)->bool`; `build_body(citation, title, url, reachable)->str`; `pull(manifest_path, dest_dir)->list[Path]` — consistent across tasks.
- **Safety:** explicit `git add` paths throughout; no `git add -A`.
