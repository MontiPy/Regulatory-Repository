# China GB Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the 49 China `cn-gb-*` regulation stubs with official metadata (title, status, implementation date, adopted-standard cross-reference, stable source link) pulled from `openstd.samr.gov.cn`, preserving the existing LLM tags and UN-equivalent cross-references.

**Architecture:** A new `connectors/china.py` (shaped like `connectors/brazil.py`) driven by a new `manifests/cn.yaml`, registered in `scripts/pull.py`. For each GB number it searches openstd, resolves the standard's `hcno`, fetches the `newGbInfo` detail page, parses metadata, and writes a record via the shared `connectors._common.write_md` — which already preserves tag fields; the connector additionally unions the openstd adopted-standard into the existing grounded `un_equivalent` and carries `un_equivalent_ai` through untouched. Failures fall back to an enriched stub.

**Tech Stack:** Python 3.14, `requests` (via `connectors._common.RateLimitedSession`), `python-frontmatter`, PyYAML, `re` (HTML parsed with regex, matching the repo's existing connector style), pytest with saved HTML fixtures (no live network in tests).

**Spec:** `docs/superpowers/specs/2026-06-04-china-gb-connector-design.md`

---

## File Structure

- `manifests/cn.yaml` (create) — `records:` list of `{id, gb_number, source_url}`, one per existing `cn-gb-*` stub.
- `connectors/china.py` (create) — the connector: `search_hcno`, `fetch_detail`, `parse_detail`, `build_body`, `enriched_stub_body`, `_merge_un_equivalent`, `_load_existing`, `pull`.
- `scripts/pull.py` (modify) — register `"CN"` in `REGION_CONNECTOR`.
- `tests/fixtures/china/` (already captured) — `std_list_gb11551.html`, `newGbInfo_gb11551.html`, `newGbInfo_gb14166.html`.
- `tests/test_china.py` (create) — fixture-backed unit + integration tests.

**Verified openstd facts (from the captured fixtures):**
- Search rows: `onclick="showInfo('<32-hex HCNO>');">GB 11551-2014</a>`.
- Detail page is a flat sequence of `label … value … label …`. Reliable labels/values: `标准号`→`GB 11551-2014`, `中文标准名称`→Chinese title, `英文标准名称`→English title, `标准状态`→`现行` (in-force), `实施日期`→`2015-01-01`. The `采用国际标准` (adopted-standard) row is frequently absent and its bare-label template occurrence has no value — extract it best-effort only.

---

## Task 1: Manifest + connector skeleton with `search_hcno`

**Files:**
- Create: `manifests/cn.yaml`
- Create: `connectors/china.py`
- Test: `tests/test_china.py`
- Commit fixtures: `tests/fixtures/china/*.html` (already on disk)

- [ ] **Step 1: Generate `manifests/cn.yaml` from the existing stubs**

Run this one-off generator (it reads the 49 stubs and writes the manifest):

```python
# scripts-scratch (run once, do not commit this snippet):
import frontmatter, glob, os, yaml
records = []
for p in sorted(glob.glob("regulations/cn-gb-*.md")):
    post = frontmatter.load(p)
    records.append({
        "id": os.path.basename(p)[:-3],
        "gb_number": str(post.get("citation", "")).strip(),
        "source_url": str(post.get("source_url", "")).strip(),
    })
with open("manifests/cn.yaml", "w", encoding="utf-8") as fh:
    yaml.safe_dump({"region": "CN", "records": records}, fh, allow_unicode=True, sort_keys=False)
print(len(records), "entries")
```
Expected: `49 entries`, and `manifests/cn.yaml` starts like:
```yaml
region: CN
records:
- id: cn-gb-11551-2014
  gb_number: GB 11551-2014
  source_url: https://openstd.samr.gov.cn/bzgk/std/index?keyword=GB%2011551-2014
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_china.py
from pathlib import Path
from connectors.china import search_hcno

FIX = Path(__file__).parent / "fixtures" / "china"

class FakeResp:
    def __init__(self, text): self.text = text; self.encoding = "utf-8"
    def raise_for_status(self): pass

class FakeSession:
    """Returns a fixed page for any .get(), recording the URL."""
    def __init__(self, text): self._text = text; self.urls = []
    def get(self, url, **kw): self.urls.append(url); return FakeResp(self._text)
    def close(self): pass

def test_search_hcno_exact_version():
    html = (FIX / "std_list_gb11551.html").read_text(encoding="utf-8")
    session = FakeSession(html)
    hcno, label = search_hcno(session, "GB 11551-2014")
    assert hcno == "290A78A7D1665437A160104DCE7FA380"
    assert label == "GB 11551-2014"

def test_search_hcno_returns_none_when_absent():
    session = FakeSession("<html><body>no results</body></html>")
    assert search_hcno(session, "GB 99999-2099") is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_china.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'connectors.china'`

- [ ] **Step 4: Implement the skeleton + `search_hcno`**

```python
# connectors/china.py
"""China GB standards connector — metadata enrichment from openstd.samr.gov.cn.

Resolves each GB number to its official record on the national standards portal
and writes title / status / implementation date / adopted-standard cross-reference.
Full text is image-based on the portal and is not captured. Existing LLM tags and
UN-equivalent cross-references on the target file are preserved.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import frontmatter
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, write_md

try:
    from scripts.un_refs import normalize_un
except ImportError:  # when run as a script from repo root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from un_refs import normalize_un

BASE = "https://openstd.samr.gov.cn/bzgk/gb"

# A search-result row: showInfo('<HCNO>'); ... > GB 11551-2014 </a>
_ROW_RE = re.compile(r"showInfo\('([0-9A-Fa-f]{32})'\)[^>]*>\s*(GB[^<]+?)\s*</a>")


def search_hcno(session: Any, gb_number: str) -> tuple[str, str] | None:
    """Return (hcno, matched_label) for a GB number, or None if not found.

    Searches the bare GB number; for a versioned query returns the exact-version
    row, otherwise the most recent version (by trailing year).
    """
    bare = gb_number.split("-")[0].strip()
    resp = session.get(f"{BASE}/std_list?p.p2={quote(bare)}")
    resp.encoding = "utf-8"
    pairs = [(h.upper(), lbl.strip()) for h, lbl in _ROW_RE.findall(resp.text)]
    if not pairs:
        return None
    target = gb_number.strip()
    for hcno, label in pairs:
        if label == target:
            return (hcno, label)

    def year(label: str) -> int:
        m = re.search(r"-(\d{4})$", label)
        return int(m.group(1)) if m else 0

    return max(pairs, key=lambda p: year(p[1]))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_china.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add manifests/cn.yaml connectors/china.py tests/test_china.py tests/fixtures/china/std_list_gb11551.html tests/fixtures/china/newGbInfo_gb11551.html tests/fixtures/china/newGbInfo_gb14166.html
git commit -m "feat(cn): China GB connector skeleton + manifest + openstd search resolver"
```
Use explicit paths — never `git add -A`/`.`.

---

## Task 2: `parse_detail` — metadata extraction

**Files:**
- Modify: `connectors/china.py`
- Test: `tests/test_china.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_china.py  (append)
from connectors.china import parse_detail

def test_parse_detail_real_fixture():
    html = (FIX / "newGbInfo_gb11551.html").read_text(encoding="utf-8")
    meta = parse_detail(html)
    assert meta["en_title"] == "The protection of the occupants in the event of a frontal collision for motor vehicle"
    assert meta["cn_title"] == "汽车正面碰撞的乘员保护"
    assert meta["status"] == "in-force"
    assert meta["impl_date"] == "2015-01-01"
    assert meta["adopted_standard"] is None  # this record declares none

def test_parse_detail_extracts_adopted_standard():
    # Minimal crafted snippet exercising the (sparsely populated) adopted-standard row.
    html = "<div>采用国际标准</div><div class='content'>ECE R94 (MOD)</div><div>主管部门</div>"
    meta = parse_detail(html)
    assert meta["adopted_standard"] == "ECE R94"

def test_parse_detail_missing_fields_are_none():
    meta = parse_detail("<html><body>nothing here</body></html>")
    assert meta["en_title"] is None
    assert meta["status"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_china.py -k parse_detail -v`
Expected: FAIL with `ImportError: cannot import name 'parse_detail'`

- [ ] **Step 3: Implement**

Add to `connectors/china.py`:

```python
# Detail-page field labels, in roughly the order they appear. _field() captures
# the text between a label and whichever of these labels comes next.
_LABELS = [
    "标准号", "中文标准名称", "英文标准名称", "标准状态", "在线预览", "下载",
    "实施信息", "中国标准分类", "国际标准分类", "发布日期", "实施日期",
    "主管部门", "归口部门", "发布单位", "备注", "采用国际标准",
]


def _field(html: str, label: str) -> str | None:
    """Text between the first occurrence of *label* and the next known label."""
    i = html.find(label)
    if i < 0:
        return None
    rest = html[i + len(label):]
    cut = len(rest)
    for other in _LABELS:
        j = rest.find(other)
        if 0 <= j < cut:
            cut = j
    text = re.sub(r"<[^>]+>", " ", rest[:cut])
    text = text.replace("：", " ").replace(":", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _status(html: str) -> str | None:
    raw = _field(html, "标准状态") or ""
    if "现行" in raw:
        return "in-force"
    if any(tok in raw for tok in ("废止", "被代替", "作废", "已作废")):
        return "abolished"
    return None


def _impl_date(html: str) -> str | None:
    raw = _field(html, "实施日期") or ""
    m = re.search(r"\d{4}-\d{2}-\d{2}", raw)
    return m.group(0) if m else None


def _adopted(html: str) -> str | None:
    """Best-effort adopted-standard token; None when the row is absent/empty."""
    raw = _field(html, "采用国际标准") or ""
    m = re.search(r"(?:ECE|UN|ISO|IEC)\s?R?\s?\d+[A-Za-z]?", raw)
    return m.group(0).replace("  ", " ").strip() if m else None


def parse_detail(html: str) -> dict[str, Any]:
    return {
        "cn_title": _field(html, "中文标准名称"),
        "en_title": _field(html, "英文标准名称"),
        "status": _status(html),
        "impl_date": _impl_date(html),
        "adopted_standard": _adopted(html),
    }
```

Note: in `test_parse_detail_extracts_adopted_standard` the expected value is `"ECE R94"`. `_adopted`'s regex `(?:ECE|UN|ISO|IEC)\s?R?\s?\d+[A-Za-z]?` matches `ECE R94` from `ECE R94 (MOD)`. Confirm the regex yields exactly `ECE R94` (it stops before ` (MOD)`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_china.py -v`
Expected: PASS (all). If `_field` over-captures for `中文标准名称`/`英文标准名称`, confirm `英文标准名称` and `标准状态` are in `_LABELS` so the title is bounded correctly.

- [ ] **Step 5: Commit**

```bash
git add connectors/china.py tests/test_china.py
git commit -m "feat(cn): parse openstd detail page (title/status/date/adopted-standard)"
```

---

## Task 3: `build_body`, `enriched_stub_body`, `_merge_un_equivalent`

**Files:**
- Modify: `connectors/china.py`
- Test: `tests/test_china.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_china.py  (append)
from connectors.china import build_body, enriched_stub_body, _merge_un_equivalent

def test_build_body_has_title_status_and_link():
    meta = {"cn_title": "汽车正面碰撞的乘员保护",
            "en_title": "Frontal collision occupant protection",
            "status": "in-force", "impl_date": "2015-01-01", "adopted_standard": "ECE R94"}
    body = build_body(meta, "GB 11551-2014", "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=ABC")
    assert "GB 11551-2014" in body
    assert "Frontal collision occupant protection" in body
    assert "In-force" in body or "in-force" in body
    assert "2015-01-01" in body
    assert "ECE R94" in body
    assert "newGbInfo?hcno=ABC" in body

def test_enriched_stub_body_notes_unresolved():
    body = enriched_stub_body("GB 99999", "https://example.test/x")
    assert "GB 99999" in body
    assert "official" in body.lower()

def test_merge_un_equivalent_unions_un_ref_only():
    # Existing grounded value preserved; ECE adopted-standard normalized + added.
    assert _merge_un_equivalent(["UN R94"], "ECE R16") == ["UN R94", "UN R16"]
    # ISO adopted standard is NOT a UN reg -> not added to un_equivalent.
    assert _merge_un_equivalent(["UN R94"], "ISO 6487") == ["UN R94"]
    # No duplicates.
    assert _merge_un_equivalent(["UN R94"], "ECE R94") == ["UN R94"]
    # None adopted -> unchanged.
    assert _merge_un_equivalent(["UN R94"], None) == ["UN R94"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_china.py -k "build_body or stub or merge" -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

Add to `connectors/china.py`:

```python
def _merge_un_equivalent(existing: list[str], adopted_standard: str | None) -> list[str]:
    """Union existing grounded UN refs with the adopted-standard ref when it is a
    UN/ECE regulation. ISO/IEC standards are not UN regs and are excluded."""
    out = list(existing or [])
    if adopted_standard:
        canon = normalize_un(adopted_standard.replace("ECE", "UN"))
        if canon and canon not in out:
            out.append(canon)
    return out


def build_body(meta: dict[str, Any], gb_number: str, source_url: str) -> str:
    en = (meta.get("en_title") or "").strip()
    cn = (meta.get("cn_title") or "").strip()
    head = f"{gb_number} — {en}" if en else gb_number
    status = meta.get("status") or "unknown"
    status_disp = {"in-force": "In-force", "abolished": "Abolished"}.get(status, status)

    lines = [f"# {head}", "", f"**Standard No.:** {gb_number}"]
    if cn:
        lines.append(f"**Chinese title:** {cn}")
    status_line = f"**Status:** {status_disp}"
    if meta.get("impl_date"):
        status_line += f"  **Implementation date:** {meta['impl_date']}"
    lines.append(status_line)
    if meta.get("adopted_standard"):
        lines.append(f"**Adopted international standard:** {meta['adopted_standard']}")
    lines += [
        "",
        "Full standard text is published by SAC and viewed through the official "
        "portal's online reader (image-based; not reproduced here).",
        "",
        f"[Official record — openstd.samr.gov.cn]({source_url})",
    ]
    return "\n".join(lines)


def enriched_stub_body(gb_number: str, source_url: str) -> str:
    link = f"[{source_url}]({source_url})" if source_url else "the official portal"
    return (
        f"# {gb_number}\n\n"
        f"**Standard No.:** {gb_number}\n\n"
        f"This standard could not be resolved on the official portal "
        f"(openstd.samr.gov.cn) automatically. Visit {link} for the official record."
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_china.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add connectors/china.py tests/test_china.py
git commit -m "feat(cn): build_body + enriched stub + UN-equivalent union merge"
```

---

## Task 4: `pull()` with frontmatter-preserving merge + register in pull.py

**Files:**
- Modify: `connectors/china.py`
- Modify: `scripts/pull.py:24-32` (`REGION_CONNECTOR`)
- Test: `tests/test_china.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/test_china.py  (append)
import frontmatter
from connectors.china import pull

def _make_manifest(tmp_path, entry):
    import yaml
    mpath = tmp_path / "cn.yaml"
    mpath.write_text(yaml.safe_dump({"region": "CN", "records": [entry]}, allow_unicode=True), encoding="utf-8")
    return mpath

def test_pull_preserves_tags_and_unions_equivalents(tmp_path, monkeypatch):
    # Pre-existing tagged stub with grounded + AI equivalents.
    dest = tmp_path / "regs"; dest.mkdir()
    existing = frontmatter.Post(
        "old body",
        id="cn-gb-11551-2014", title="Old spreadsheet title", region="CN",
        citation="GB 11551-2014", status="in-force",
        source_url="https://old", source_api="spreadsheet",
        tagging_status="llm-tagged", commodities=["Airbags"], systems=["Crashworthiness"],
        un_equivalent=["UN R94"], un_equivalent_ai=["UN R16"],
    )
    (dest / "cn-gb-11551-2014.md").write_text(frontmatter.dumps(existing), encoding="utf-8")

    # Stub the network: search -> fixture list; detail -> fixture detail (no adopted std).
    import connectors.china as china
    list_html = (FIX / "std_list_gb11551.html").read_text(encoding="utf-8")
    detail_html = (FIX / "newGbInfo_gb11551.html").read_text(encoding="utf-8")
    monkeypatch.setattr(china, "RateLimitedSession", lambda **kw: FakeSession(list_html))
    monkeypatch.setattr(china, "fetch_detail", lambda session, hcno: detail_html)

    manifest = _make_manifest(tmp_path, {
        "id": "cn-gb-11551-2014", "gb_number": "GB 11551-2014", "source_url": "https://old",
    })
    pull(manifest, dest)

    post = frontmatter.load(dest / "cn-gb-11551-2014.md")
    assert post["source_api"] == "china"
    assert post["commodities"] == ["Airbags"]          # tag preserved by write_md
    assert post["tagging_status"] == "llm-tagged"
    assert post["un_equivalent"] == ["UN R94"]          # grounded preserved (no adopted here)
    assert post["un_equivalent_ai"] == ["UN R16"]       # AI carried through
    assert "occupants" in post["title"]                 # official EN title applied
    assert "Old spreadsheet title" in post.get("aliases", [])  # prior title demoted
    assert "newGbInfo" in post["source_url"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_china.py -k pull -v`
Expected: FAIL with `ImportError: cannot import name 'pull'` (or `fetch_detail`).

- [ ] **Step 3: Implement `fetch_detail`, `_load_existing`, and `pull`**

Add to `connectors/china.py`:

```python
def fetch_detail(session: Any, hcno: str) -> str:
    resp = session.get(f"{BASE}/newGbInfo?hcno={hcno}")
    resp.encoding = "utf-8"
    return resp.text


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
    pulled: list[Path] = []
    failed: list[str] = []

    for entry in manifest.get("records", []):
        file_id = str(entry.get("id", "")).strip()
        gb = str(entry.get("gb_number", "")).strip()
        fallback_url = str(entry.get("source_url", "")).strip()
        if not file_id or not gb:
            continue

        existing = _load_existing(dest_dir / f"{file_id}.md")
        meta: dict[str, Any] = {}
        print(f"  Pulling CN {gb} ...", end=" ", flush=True)
        try:
            found = search_hcno(session, gb)
            if not found:
                raise LookupError("not found on openstd")
            hcno, label = found
            source_url = f"{BASE}/newGbInfo?hcno={hcno}"
            meta = parse_detail(fetch_detail(session, hcno))
            citation = label
            title = meta.get("en_title") or meta.get("cn_title") or existing.get("title") or label
            status = meta.get("status") or existing.get("status") or "in-force"
            body = build_body(meta, citation, source_url)
            print(f"OK ({'in-force' if status=='in-force' else status})")
        except Exception as exc:
            citation = existing.get("citation") or gb
            source_url = fallback_url or existing.get("source_url") or ""
            title = existing.get("title") or gb
            status = existing.get("status") or "in-force"
            body = enriched_stub_body(gb, source_url)
            failed.append(f"{gb}: {exc}")
            print(f"STUB ({exc})")

        record: dict[str, Any] = {
            "id": file_id, "title": title, "region": "CN", "citation": citation,
            "status": status, "source_url": source_url or fallback_url or f"{BASE}/std/index",
            "source_api": "china",
            "tagging_status": existing.get("tagging_status", "untagged"),
        }
        un_eq = _merge_un_equivalent(existing.get("un_equivalent", []), meta.get("adopted_standard"))
        if un_eq:
            record["un_equivalent"] = un_eq
        for field in ("un_equivalent_ai", "translation_status", "paywall", "tagged_at"):
            if existing.get(field) not in (None, [], ""):
                record[field] = existing[field]
        aliases = list(existing.get("aliases", []) or [])
        prev_title = existing.get("title")
        if prev_title and prev_title != title and prev_title not in aliases:
            aliases.append(prev_title)
        if aliases:
            record["aliases"] = sorted(set(aliases))
        if meta.get("impl_date"):
            record["effective_date"] = meta["impl_date"]

        pulled.append(write_md(record, body, dest_dir))

    session.close()
    if failed:
        print(f"\n{len(failed)} fell back to stub:")
        for msg in failed:
            print(f"  {msg}")
    return pulled
```

- [ ] **Step 4: Register the connector in `scripts/pull.py`**

In `REGION_CONNECTOR` (after the `"BR"` line) add:
```python
    "CN": ("connectors.china", "manifests/cn.yaml"),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_china.py -v`
Expected: PASS (all). Then full suite: `python -m pytest -q` → all PASS.

- [ ] **Step 6: Commit**

```bash
git add connectors/china.py scripts/pull.py tests/test_china.py
git commit -m "feat(cn): pull() with frontmatter-preserving merge; register CN connector"
```

---

## Task 5: Live pull + build verification

**Files:**
- Modify: `regulations/cn-gb-*.md` (regenerated by the connector)

- [ ] **Step 1: Run the live connector**

Run: `python scripts/pull.py --region CN`
Expected: 49 lines, mostly `OK (in-force)`, a few `STUB (...)` for any GB number openstd cannot resolve. No traceback.

- [ ] **Step 2: Spot-check enrichment preserved tags + equivalents**

Run:
```bash
python -c "import frontmatter; p=frontmatter.load('regulations/cn-gb-11551-2014.md'); print('api:',p.get('source_api')); print('tags:',p.get('commodities')); print('un:',p.get('un_equivalent'),'ai:',p.get('un_equivalent_ai')); print('title:',p.get('title')); print('status:',p.get('status'))"
```
Expected: `api: china`; `commodities` non-empty (preserved); `un`/`ai` still present; `title` is the official English title; `status: in-force`.

- [ ] **Step 3: Build and confirm no regressions**

Run: `python scripts/build.py` then `python -m pytest -q`
Expected: `Build complete: 728 records, 0 errors, 0 warnings`; all tests pass. (Record count unchanged — the connector rewrites existing files, it does not add or remove records.)

- [ ] **Step 4: Commit the regenerated records**

```bash
git add regulations
git commit -m "data(cn): enrich 49 China GB records with official openstd metadata"
```
Use explicit `git add regulations` — never `git add -A`/`.`.

---

## Self-Review Checklist (run after implementation)

- **Spec coverage:** manifest+connector+registration (Tasks 1,4) ✓; openstd search→detail→parse (Tasks 1,2) ✓; metadata-only body (Task 3) ✓; frontmatter-preserving merge incl. `un_equivalent` union + `un_equivalent_ai` carry-through (Task 4) ✓; enriched-stub fallback (Tasks 3,4) ✓; fixture-based tests incl. preservation (Tasks 1-4) ✓; live verification (Task 5) ✓.
- **Out of scope honored:** no full-text capture; GCC/India/Vietnam untouched; `effective_date` written to frontmatter but not surfaced (pre-existing build gap).
- **Type consistency:** `search_hcno` returns `(hcno, label)|None`; `parse_detail` returns the 5-key dict consumed by `build_body`/`pull`; `_merge_un_equivalent(existing, adopted)` signature stable across Tasks 3-4.
- **Safety:** explicit `git add` paths throughout; no `git add -A`.
