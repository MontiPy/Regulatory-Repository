# Phase 1 — Build/Data Rearchitecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the build from emitting one ~16 MB inline `dist/index.html` into a hosted-ready static bundle — a lightweight `data/index.json`, lazy per-record body files, a client-side search corpus, separated CSS/JS, and a minimal HTML shell — **while preserving the current faceted-search UI exactly.**

**Architecture:** `build.py` stops embedding records in the template. Instead it writes `dist/data/index.json` (light metadata, no bodies), `dist/data/records/<id>.json` (one body per record, fetched on demand), `dist/data/taxonomy.json` (vocabularies + region→series map), and `dist/data/search-text.json` (per-record searchable text incl. capped body plaintext). The HTML shell loads `assets/styles.css` + `assets/app.js`; `app.js` fetches `index.json` on load, lazy-fetches bodies on expand, and builds a MiniSearch index in-browser (vendored) for full-text search. The visible UI (header search, left facet rail, result cards, expand-in-place) is unchanged this phase — this de-risks the data/build split before any new IA (Home/Workspace) lands in Phase 2/3.

**Tech Stack:** Python 3.10+ (build), pytest, Jinja2, bleach, markdown, frontmatter, PyYAML; vanilla JS + [MiniSearch](https://github.com/lucaong/minisearch) (vendored UMD build) on the client. No Node build step.

---

## Scope & boundaries

- **In scope:** build.py bundle emission; `taxonomy.yaml` region→series map; split of the inline template into shell + `assets/styles.css` + `assets/app.js`; async data loading; lazy bodies; client search index; updated `tests/test_build.py`; manual browser smoke test.
- **Out of scope (Phase 2/3):** Home view, Workspace, filter chips, group-by-market, side reading pane. Do **not** change the visible layout this phase.
- **Coexistence note:** A background agent is auto-tagging `regulations/*.md` on branch `chore/auto-tag-backlog`. This plan does **not** touch `regulations/*.md`; only consumes them at build time. Work on a fresh branch off `main`: `phase1-build-rearchitecture`.

## File structure

| File | Responsibility |
|---|---|
| `scripts/build.py` (modify) | Emit the bundle instead of one HTML file. New funcs: `load_region_series`, `split_record`, `search_text_for`, `write_index_json`, `write_record_bodies`, `write_taxonomy_json`, `write_search_text`, `copy_static_assets`, `render_shell`. Replace `render_index` call in `build()`. |
| `taxonomy.yaml` (modify) | Add `region_series:` map (per region: `series`, `name`). |
| `templates/index.html.j2` (replace) | Minimal shell: head, `<link>`/`<script>` to assets, footer build meta, empty mount points. No embedded data. |
| `assets/styles.css` (create) | The CSS currently inlined in the template, verbatim. Build copies it to `dist/assets/`. |
| `assets/app.js` (create) | The JS currently inlined, modified for async data + lazy bodies + MiniSearch. Build copies it to `dist/assets/`. |
| `assets/vendor/minisearch.min.js` (create) | Vendored MiniSearch UMD build, committed. |
| `tests/test_build.py` (modify) | Add tests for the new build functions + an integration test asserting the emitted bundle structure. |
| `tests/fixtures/regs/*.md` (create) | 2–3 tiny fixture records for the integration test. |

**Source-of-truth for assets:** `assets/` at repo root holds the editable CSS/JS/vendor; `build.py` copies `assets/` → `dist/assets/`. Edit under `assets/`, never under `dist/`.

---

## Task 1: Region→series map in taxonomy.yaml

**Files:**
- Modify: `taxonomy.yaml`
- Modify: `scripts/build.py` (add `load_region_series`)
- Test: `tests/test_build.py`

- [ ] **Step 1: Add the map to `taxonomy.yaml`**

Append this top-level key (confirmed labels from connectors; EU + long-tail are best-effort and tracked in TODO.md):

```yaml
region_series:
  US:   { series: FMVSS,   name: United States }
  CA:   { series: CMVSS,   name: Canada }
  KR:   { series: KMVSS,   name: South Korea }
  AU:   { series: ADR,     name: Australia }
  ECE:  { series: UN R,    name: UNECE }
  JP:   { series: JVSR,    name: Japan }
  BR:   { series: CONTRAN, name: Brazil }
  CN:   { series: GB,      name: China }
  GCC:  { series: GSO,     name: Gulf Cooperation Council }
  IN:   { series: AIS,     name: India }
  EU:   { series: EU,      name: European Union }
  OTHER:{ series: "",      name: Other }
```

- [ ] **Step 2: Write the failing test**

In `tests/test_build.py`, add near the imports: `from scripts.build import load_region_series`. Then:

```python
class TestLoadRegionSeries:
    def test_known_region_has_series_and_name(self):
        mapping = load_region_series()
        assert mapping["US"]["series"] == "FMVSS"
        assert mapping["US"]["name"] == "United States"

    def test_returns_dict(self):
        assert isinstance(load_region_series(), dict)
```

- [ ] **Step 3: Run it, expect failure**

Run: `python -m pytest tests/test_build.py::TestLoadRegionSeries -v`
Expected: FAIL — `ImportError: cannot import name 'load_region_series'`.

- [ ] **Step 4: Implement `load_region_series`**

In `scripts/build.py`, after `load_taxonomy`:

```python
def load_region_series() -> dict[str, dict[str, str]]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    series = raw.get("region_series", {}) or {}
    return {
        str(region): {
            "series": str((entry or {}).get("series", "")),
            "name": str((entry or {}).get("name", region)),
        }
        for region, entry in series.items()
    }
```

- [ ] **Step 5: Run it, expect pass**

Run: `python -m pytest tests/test_build.py::TestLoadRegionSeries -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add taxonomy.yaml scripts/build.py tests/test_build.py
git commit -m "feat(build): add region->series mapping loader"
```

---

## Task 2: Split a record into light index entry + body

**Files:**
- Modify: `scripts/build.py` (add `split_record`)
- Test: `tests/test_build.py`

The light entry is everything the Home/Workspace and facets need **except** `body_html`. `summary_text` stays in the light entry (it's short, derived).

- [ ] **Step 1: Write the failing test**

```python
from scripts.build import split_record  # add to imports

class TestSplitRecord:
    FULL = {
        "id": "us-fmvss-208", "title": "Occupant crash protection",
        "region": "US", "citation": "49 CFR §571.208", "status": "in-force",
        "source_url": "https://example.com", "source_api": "ecfr",
        "last_pulled": "2026-01-01T00:00:00+00:00", "tagging_status": "llm-tagged",
        "tagged_at": "", "aliases": [], "commodities": ["Airbags"],
        "systems": ["Crashworthiness"], "vehicle_categories": ["Passenger car"],
        "un_equivalent": [], "related": [], "tags": [], "paywall": False,
        "translation_status": "", "summary_text": "A summary.",
        "body_html": "<p>Long body…</p>",
    }

    def test_light_omits_body(self):
        light, body = split_record(self.FULL)
        assert "body_html" not in light
        assert body == "<p>Long body…</p>"

    def test_light_keeps_summary_and_tags(self):
        light, _ = split_record(self.FULL)
        assert light["summary_text"] == "A summary."
        assert light["commodities"] == ["Airbags"]

    def test_body_defaults_empty(self):
        full = dict(self.FULL); del full["body_html"]
        _, body = split_record(full)
        assert body == ""
```

- [ ] **Step 2: Run it, expect failure**

Run: `python -m pytest tests/test_build.py::TestSplitRecord -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement `split_record`**

```python
def split_record(record: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Return (light_entry_without_body, body_html)."""
    light = {key: value for key, value in record.items() if key != "body_html"}
    return light, record.get("body_html", "")
```

- [ ] **Step 4: Run it, expect pass**

Run: `python -m pytest tests/test_build.py::TestSplitRecord -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build.py tests/test_build.py
git commit -m "feat(build): split_record into light entry + body"
```

---

## Task 3: Searchable text (capped body plaintext)

**Files:**
- Modify: `scripts/build.py` (add `search_text_for`)
- Test: `tests/test_build.py`

Per-record search blob: title + citation + aliases + tags + summary + body plaintext, with body plaintext **capped at 20 000 chars** so the 1–3 MB outliers don't dominate the index. Reuses the existing `bleach.clean(..., tags=[])` plaintext approach from `summarize`.

- [ ] **Step 1: Write the failing test**

```python
from scripts.build import search_text_for  # add to imports

class TestSearchTextFor:
    def test_includes_title_and_body_plain(self):
        rec = {"id": "x", "title": "Brakes", "citation": "C1", "aliases": [],
               "tags": [], "commodities": ["Brakes"], "systems": ["Braking"],
               "vehicle_categories": [], "summary_text": "sum",
               "body_html": "<p>Hydraulic <strong>brake</strong> lines.</p>"}
        blob = search_text_for(rec)
        assert blob["id"] == "x"
        assert "Brakes" in blob["text"]
        assert "Hydraulic brake lines." in blob["text"]
        assert "<strong>" not in blob["text"]

    def test_body_capped(self):
        rec = {"id": "y", "title": "", "citation": "", "aliases": [], "tags": [],
               "commodities": [], "systems": [], "vehicle_categories": [],
               "summary_text": "", "body_html": "<p>" + "x" * 50000 + "</p>"}
        blob = search_text_for(rec)
        assert len(blob["text"]) <= 20100  # 20k body cap + small header fields
```

- [ ] **Step 2: Run it, expect failure**

Run: `python -m pytest tests/test_build.py::TestSearchTextFor -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement `search_text_for`**

```python
SEARCH_BODY_CAP = 20000

def _plain_text(body_html: str) -> str:
    plain = bleach.clean(body_html or "", tags=[], strip=True)
    return unescape(re.sub(r"\s+", " ", plain)).strip()

def search_text_for(record: dict[str, Any]) -> dict[str, str]:
    parts = [
        stringify(record.get("title")),
        stringify(record.get("citation")),
        " ".join(record.get("aliases", [])),
        " ".join(record.get("tags", [])),
        " ".join(record.get("commodities", [])),
        " ".join(record.get("systems", [])),
        " ".join(record.get("vehicle_categories", [])),
        stringify(record.get("summary_text")),
        _plain_text(record.get("body_html", ""))[:SEARCH_BODY_CAP],
    ]
    return {"id": stringify(record.get("id")), "text": " ".join(p for p in parts if p)}
```

- [ ] **Step 4: Run it, expect pass**

Run: `python -m pytest tests/test_build.py::TestSearchTextFor -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build.py tests/test_build.py
git commit -m "feat(build): per-record searchable text with capped body plaintext"
```

---

## Task 4: Write the data bundle (index, bodies, taxonomy, search)

**Files:**
- Modify: `scripts/build.py` (add `write_index_json`, `write_record_bodies`, `write_taxonomy_json`, `write_search_text`)
- Test: `tests/test_build.py`

All writers take an explicit `dist_dir: Path` so tests can use `tmp_path`.

- [ ] **Step 1: Write the failing test**

```python
import json
from scripts.build import (  # add to imports
    write_index_json, write_record_bodies, write_taxonomy_json, write_search_text,
)

class TestBundleWriters:
    RECORDS = [
        {"id": "a", "title": "A", "region": "US", "citation": "c", "status": "in-force",
         "source_url": "", "source_api": "ecfr", "last_pulled": "", "tagging_status": "untagged",
         "tagged_at": "", "aliases": [], "commodities": [], "systems": [],
         "vehicle_categories": [], "un_equivalent": [], "related": [], "tags": [],
         "paywall": False, "translation_status": "", "summary_text": "sa",
         "body_html": "<p>body a</p>"},
    ]

    def test_index_json_has_no_bodies(self, tmp_path):
        write_index_json(self.RECORDS, tmp_path)
        data = json.loads((tmp_path / "data" / "index.json").read_text(encoding="utf-8"))
        assert data[0]["id"] == "a"
        assert "body_html" not in data[0]
        assert data[0]["summary_text"] == "sa"

    def test_record_bodies_one_file_each(self, tmp_path):
        write_record_bodies(self.RECORDS, tmp_path)
        body = json.loads((tmp_path / "data" / "records" / "a.json").read_text(encoding="utf-8"))
        assert body["id"] == "a"
        assert body["body_html"] == "<p>body a</p>"

    def test_taxonomy_json_includes_region_series(self, tmp_path):
        write_taxonomy_json({"regions": ["US"]}, {"US": {"series": "FMVSS", "name": "United States"}}, tmp_path)
        data = json.loads((tmp_path / "data" / "taxonomy.json").read_text(encoding="utf-8"))
        assert data["regions"] == ["US"]
        assert data["region_series"]["US"]["series"] == "FMVSS"

    def test_search_text_one_entry_each(self, tmp_path):
        write_search_text(self.RECORDS, tmp_path)
        data = json.loads((tmp_path / "data" / "search-text.json").read_text(encoding="utf-8"))
        assert data[0]["id"] == "a"
        assert "body a" in data[0]["text"]
```

- [ ] **Step 2: Run it, expect failure**

Run: `python -m pytest tests/test_build.py::TestBundleWriters -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement the writers**

```python
def _ensure_data_dir(dist_dir: Path) -> Path:
    data_dir = dist_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def write_index_json(records: list[dict[str, Any]], dist_dir: Path) -> None:
    light = [split_record(r)[0] for r in records]
    data_dir = _ensure_data_dir(dist_dir)
    (data_dir / "index.json").write_text(
        json.dumps(light, ensure_ascii=False), encoding="utf-8"
    )

def write_record_bodies(records: list[dict[str, Any]], dist_dir: Path) -> None:
    records_dir = _ensure_data_dir(dist_dir) / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        rec_id = stringify(record.get("id"))
        if not rec_id:
            continue
        _light, body = split_record(record)
        (records_dir / f"{rec_id}.json").write_text(
            json.dumps({"id": rec_id, "body_html": body}, ensure_ascii=False),
            encoding="utf-8",
        )

def write_taxonomy_json(
    taxonomy: dict[str, list[str]],
    region_series: dict[str, dict[str, str]],
    dist_dir: Path,
) -> None:
    payload = dict(taxonomy)
    payload["region_series"] = region_series
    data_dir = _ensure_data_dir(dist_dir)
    (data_dir / "taxonomy.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

def write_search_text(records: list[dict[str, Any]], dist_dir: Path) -> None:
    blobs = [search_text_for(r) for r in records]
    data_dir = _ensure_data_dir(dist_dir)
    (data_dir / "search-text.json").write_text(
        json.dumps(blobs, ensure_ascii=False), encoding="utf-8"
    )
```

- [ ] **Step 4: Run it, expect pass**

Run: `python -m pytest tests/test_build.py::TestBundleWriters -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/build.py tests/test_build.py
git commit -m "feat(build): bundle writers for index/bodies/taxonomy/search"
```

---

## Task 5: Extract CSS to assets/styles.css and copy it

**Files:**
- Create: `assets/styles.css`
- Modify: `scripts/build.py` (add `copy_static_assets`)
- Test: `tests/test_build.py`

- [ ] **Step 1: Create `assets/styles.css`**

Copy the entire contents currently between `<style>` and `</style>` in `templates/index.html.j2` (lines 11–812 of the current template — all the `:root` tokens, dark-mode, layout, cards, etc.) verbatim into `assets/styles.css`. Do not change any rule this phase.

- [ ] **Step 2: Write the failing test**

```python
from scripts.build import copy_static_assets  # add to imports

class TestCopyAssets:
    def test_copies_css_and_js(self, tmp_path):
        copy_static_assets(tmp_path)
        assert (tmp_path / "assets" / "styles.css").exists()
        assert (tmp_path / "assets" / "app.js").exists()
        assert (tmp_path / "assets" / "vendor" / "minisearch.min.js").exists()
```

(This test also covers Tasks 6/7 asset files; it will stay red until `assets/app.js` and the vendor file exist — that's fine, they land in Tasks 7–8. Mark this test `@pytest.mark.xfail(reason="assets land in later tasks")` now and remove the marker in Task 8 Step 4.)

- [ ] **Step 3: Implement `copy_static_assets`**

```python
import shutil  # add to imports at top of file

ASSETS_DIR = ROOT / "assets"

def copy_static_assets(dist_dir: Path) -> None:
    dest = dist_dir / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ASSETS_DIR, dest)
```

- [ ] **Step 4: Run it**

Run: `python -m pytest tests/test_build.py::TestCopyAssets -v`
Expected: XFAIL (app.js / vendor not created yet).

- [ ] **Step 5: Commit**

```bash
git add assets/styles.css scripts/build.py tests/test_build.py
git commit -m "feat(build): extract styles.css and add asset copier"
```

---

## Task 6: Vendor MiniSearch

**Files:**
- Create: `assets/vendor/minisearch.min.js`

- [ ] **Step 1: Download the UMD build (one-time, committed)**

Run (PowerShell):

```powershell
New-Item -ItemType Directory -Force assets/vendor | Out-Null
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/minisearch@7.1.1/dist/umd/index.min.js" -OutFile "assets/vendor/minisearch.min.js"
```

- [ ] **Step 2: Verify it defines the global**

Run: `python -c "t=open('assets/vendor/minisearch.min.js',encoding='utf-8').read(); print('MiniSearch' in t, len(t))"`
Expected: `True <some length > 1000>`.

- [ ] **Step 3: Commit**

```bash
git add assets/vendor/minisearch.min.js
git commit -m "chore(assets): vendor MiniSearch 7.1.1 UMD build"
```

---

## Task 7: Extract JS to assets/app.js, load data asynchronously

**Files:**
- Create: `assets/app.js`
- Test: manual (no JS test runner in repo) + the integration test in Task 9

This moves the inline `<script>` (current template lines ~873–1369) into `assets/app.js` with three changes: (a) data comes from `fetch`, not Jinja; (b) bodies are lazy; (c) search uses MiniSearch. Keep all other functions (filters, facet counts, URL sync, theme, tooltip) unchanged.

- [ ] **Step 1: Create `assets/app.js` from the current inline script**

Copy the current inline JS verbatim, then apply the edits below. Remove the two Jinja lines at the top:

```js
// DELETE these (they were Jinja-substituted):
// const REGS = {{ records_json | safe }};
// const TAXONOMY = {{ taxonomy | safe }};
```

Replace with module-scoped state populated at startup:

```js
let REGS = [];
let TAXONOMY = {};
let recordById = new Map();
const bodyCache = new Map();      // id -> body_html (lazy)
let searchEngine = null;          // MiniSearch instance (lazy)
let searchReady = false;
```

- [ ] **Step 2: Add the data bootstrap and wrap init**

Find the current bottom-of-script init block:

```js
buildFilters();
applyUrlParams();
render();
updateClearButton();
```

Replace it with an async bootstrap that loads `index.json` + `taxonomy.json` first, then runs the existing init, then warms search after first paint:

```js
async function boot() {
  const [regs, taxonomy] = await Promise.all([
    fetch("data/index.json").then((r) => r.json()),
    fetch("data/taxonomy.json").then((r) => r.json()),
  ]);
  REGS = regs;
  TAXONOMY = taxonomy;
  recordById = new Map(REGS.map((r) => [r.id, r]));
  rebuildCorpusCounts();           // see Step 3
  buildFilters();
  applyUrlParams();
  render();
  updateClearButton();
  // Warm the search index after first paint (non-blocking).
  requestIdleCallback?.(loadSearch) ?? setTimeout(loadSearch, 0);
}
boot();
```

- [ ] **Step 3: Make `CORPUS_COUNTS` rebuildable**

The current `const CORPUS_COUNTS = (() => { … })();` runs at parse time when `REGS` was inline. Convert it to a function called after data loads:

```js
let CORPUS_COUNTS = {};
function rebuildCorpusCounts() {
  const counts = {};
  FILTERS.forEach((f) => { counts[f.key] = {}; });
  REGS.forEach((r) => {
    FILTERS.forEach((f) => {
      const raw = r[f.key];
      const vals = Array.isArray(raw) ? raw : (raw != null && raw !== "" ? [raw] : []);
      vals.forEach((v) => { counts[f.key][v] = (counts[f.key][v] || 0) + 1; });
    });
  });
  CORPUS_COUNTS = counts;
}
```

- [ ] **Step 4: Lazy-load bodies on expand**

The current `cards` click handler toggles `expanded` then calls `render()`. Bodies are no longer in `REGS`. Make expansion fetch the body first and store it in `bodyCache`; `expandedContent` reads from the cache.

Replace the cards click handler body with:

```js
cards.addEventListener("click", async (event) => {
  const btn = event.target.closest("[data-expand]");
  if (!btn) return;
  const id = btn.getAttribute("data-expand");
  if (expanded.has(id)) {
    expanded.delete(id);
  } else {
    expanded.add(id);
    if (!bodyCache.has(id)) {
      try {
        const data = await fetch(`data/records/${encodeURIComponent(id)}.json`).then((r) => r.json());
        bodyCache.set(id, data.body_html || "");
      } catch {
        bodyCache.set(id, "<p>Failed to load regulation text.</p>");
      }
    }
  }
  render();
  document.querySelector(`#reg-${CSS.escape(slug(id))}`)?.scrollIntoView({ block: "nearest" });
});
```

In `expandedContent(record)`, change the body line from `${record.body_html || ""}` to `${bodyCache.get(record.id) || ""}`.

- [ ] **Step 5: Replace body-text search with MiniSearch**

The current `matchesText` searches `r.body_html` (now absent). Split into metadata match (always available) + MiniSearch body match (when loaded):

```js
function loadSearch() {
  if (searchEngine) return;
  fetch("data/search-text.json")
    .then((r) => r.json())
    .then((docs) => {
      searchEngine = new MiniSearch({ fields: ["text"], storeFields: ["id"] });
      searchEngine.addAll(docs);
      searchReady = true;
      if (searchInput.value.trim()) render();   // re-render if user already typed
    });
}

function matchesText(r, query) {
  const q = normalize(query).trim();
  if (!q) return true;
  const base = [
    r.title, r.citation, (r.aliases || []).join(" "),
    r.summary_text, (r.un_equivalent || []).join(" "), (r.tags || []).join(" "),
  ].join(" ");
  if (normalize(base).includes(q)) return true;
  if (searchReady && q.length >= 3) return searchHitIds().has(r.id);
  return false;
}

let _lastQuery = null, _lastHits = new Set();
function searchHitIds() {
  const q = searchInput.value.trim();
  if (q === _lastQuery) return _lastHits;
  _lastQuery = q;
  _lastHits = new Set(searchEngine.search(q, { prefix: true }).map((h) => h.id));
  return _lastHits;
}
```

- [ ] **Step 6: Manual check deferred**

`app.js` can't run until the shell (Task 8) loads it and a build emits data. Verification happens in Task 9 Step 4 (build) and Task 10 (browser smoke test).

- [ ] **Step 7: Commit**

```bash
git add assets/app.js
git commit -m "feat(client): app.js with async data, lazy bodies, MiniSearch"
```

---

## Task 8: Minimal HTML shell template + render_shell

**Files:**
- Replace: `templates/index.html.j2`
- Modify: `scripts/build.py` (add `render_shell`, remove old `render_index`)
- Test: `tests/test_build.py` (remove the xfail marker from Task 5)

- [ ] **Step 1: Replace `templates/index.html.j2` with the shell**

The new template is the current `<body>` markup (header, layout, filters, main, footer) with **no `<style>` block and no inline `<script>`** — those become external references. Keep all element IDs/classes identical so `app.js` and `styles.css` work unchanged.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Regulatory Repository</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700;900&family=Noto+Sans:ital,wght@0,300;0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <!-- Paste the CURRENT template's <header>…</header> through <footer>…</footer>
       verbatim (current lines 817–871), unchanged. -->
  {{ BODY_MARKUP }}
  <script src="assets/vendor/minisearch.min.js"></script>
  <script src="assets/app.js"></script>
</body>
</html>
```

Replace `{{ BODY_MARKUP }}` with the actual header/layout/footer markup from the current template (lines 817–871). The footer build-meta line stays Jinja: `Built {{ build_meta.timestamp }} … {{ build_meta.count }} regulations … {{ build_meta.region_counts|length }} regions`.

- [ ] **Step 2: Write the failing test**

```python
from scripts.build import render_shell  # add to imports

class TestRenderShell:
    def test_shell_has_no_embedded_records(self, tmp_path):
        meta = {"timestamp": "t", "count": 1, "region_counts": {"US": 1}, "tagging_status_counts": {}}
        render_shell(meta, tmp_path)
        html = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "records_json" not in html
        assert 'src="assets/app.js"' in html
        assert 'href="assets/styles.css"' in html
        assert "1 regulations" in html or "1 regulations" in html
```

- [ ] **Step 3: Run it, expect failure**

Run: `python -m pytest tests/test_build.py::TestRenderShell -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 4: Implement `render_shell`, delete `render_index`**

```python
def render_shell(build_meta: dict[str, Any], dist_dir: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("index.html.j2")
    html = template.render(build_meta=build_meta)
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text(html, encoding="utf-8")
```

Delete the old `render_index` function entirely (its body-embedding job is gone).

- [ ] **Step 5: Remove the xfail marker** added in Task 5 Step 2 (the vendor + app.js now exist).

- [ ] **Step 6: Run both tests, expect pass**

Run: `python -m pytest tests/test_build.py::TestRenderShell tests/test_build.py::TestCopyAssets -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add templates/index.html.j2 scripts/build.py tests/test_build.py
git commit -m "feat(build): minimal HTML shell + render_shell, drop inline data"
```

---

## Task 9: Wire build() to emit the bundle + integration test

**Files:**
- Modify: `scripts/build.py` (`build()` body)
- Create: `tests/fixtures/regs/us-fmvss-208.md`, `tests/fixtures/regs/eu-sample.md`
- Test: `tests/test_build.py`

- [ ] **Step 1: Create two fixture records**

`tests/fixtures/regs/us-fmvss-208.md`:

```markdown
---
id: us-fmvss-208
title: Occupant crash protection
region: US
citation: 49 CFR §571.208
status: in-force
source_url: https://example.com/208
source_api: ecfr
last_pulled: '2026-01-01T00:00:00+00:00'
tagging_status: llm-tagged
commodities:
- Airbags
systems:
- Crashworthiness
vehicle_categories:
- Passenger car
---
# Occupant crash protection

Hydraulic brake lines and airbag deployment requirements.
```

`tests/fixtures/regs/eu-sample.md`:

```markdown
---
id: eu-sample
title: Sample EU regulation
region: EU
citation: EU 2026/1
status: in-force
source_url: https://example.com/eu
source_api: eurlex
last_pulled: '2026-01-01T00:00:00+00:00'
tagging_status: untagged
---
# Sample

Body text for the EU sample.
```

- [ ] **Step 2: Write the failing integration test**

```python
class TestBuildBundleIntegration:
    def test_emits_full_bundle(self, tmp_path, monkeypatch):
        from scripts import build as build_mod
        monkeypatch.setattr(build_mod, "REGULATIONS_DIR", Path(__file__).parent / "fixtures" / "regs")
        monkeypatch.setattr(build_mod, "DIST_DIR", tmp_path / "dist")
        rc = build_mod.build(draft=True)
        dist = tmp_path / "dist"
        assert (dist / "index.html").exists()
        assert (dist / "assets" / "app.js").exists()
        index = json.loads((dist / "data" / "index.json").read_text(encoding="utf-8"))
        ids = {r["id"] for r in index}
        assert ids == {"us-fmvss-208", "eu-sample"}
        assert all("body_html" not in r for r in index)
        assert (dist / "data" / "records" / "us-fmvss-208.json").exists()
        assert (dist / "data" / "taxonomy.json").exists()
        search = json.loads((dist / "data" / "search-text.json").read_text(encoding="utf-8"))
        assert any("brake" in s["text"].lower() for s in search)
        assert rc in (0, 1)  # draft mode: untagged eu-sample must not hard-fail
```

- [ ] **Step 3: Run it, expect failure**

Run: `python -m pytest tests/test_build.py::TestBuildBundleIntegration -v`
Expected: FAIL — `build()` still calls the deleted `render_index`.

- [ ] **Step 4: Rewrite the tail of `build()`**

Replace the `render_index(records, taxonomy)` call (and surrounding emit logic) with the bundle pipeline. The new `build()` tail, after `records` is finalized and the report is written:

```python
    region_series = load_region_series()
    region_counts = dict(Counter(r["region"] for r in records if r.get("region")))
    tagging_status_counts = dict(Counter(r["tagging_status"] for r in records if r.get("tagging_status")))
    build_meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(records),
        "region_counts": region_counts,
        "tagging_status_counts": tagging_status_counts,
    }

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    write_index_json(records, DIST_DIR)
    write_record_bodies(records, DIST_DIR)
    write_taxonomy_json(taxonomy, region_series, DIST_DIR)
    write_search_text(records, DIST_DIR)
    copy_static_assets(DIST_DIR)
    render_shell(build_meta, DIST_DIR)
```

Update the final `print(...)` to: `f"Build complete: {len(records)} records … Wrote dist/ bundle (index.html, assets/, data/)."`.

- [ ] **Step 5: Run it, expect pass**

Run: `python -m pytest tests/test_build.py::TestBuildBundleIntegration -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest tests/test_build.py -v`
Expected: PASS (all classes).

- [ ] **Step 7: Build for real and sanity-check sizes**

Run: `python scripts/build.py --draft`
Then (PowerShell): `Get-ChildItem dist/data/index.json, dist/data/search-text.json | Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,2)}}`
Expected: `index.json` and `search-text.json` each well under the page's old 16 MB; note the `search-text.json` MB for the budget check below.

- [ ] **Step 8: Budget check (record the number)**

If `dist/data/search-text.json` exceeds **~6 MB** uncompressed (rough proxy for >3 MB gzipped), lower `SEARCH_BODY_CAP` (Task 3) from 20000 to 4000 and rebuild. Record the chosen cap + resulting size in the commit message.

- [ ] **Step 9: Commit**

```bash
git add scripts/build.py tests/fixtures/regs/ tests/test_build.py
git commit -m "feat(build): emit static bundle (index/bodies/taxonomy/search/assets/shell)"
```

---

## Task 10: Browser smoke test (manual, Playwright MCP)

**Files:** none (verification only)

- [ ] **Step 1: Serve the bundle**

`fetch()` needs HTTP (not `file://`). Run (PowerShell, from repo root):
`python -m http.server 8000 --directory dist`

- [ ] **Step 2: Drive it with the Playwright MCP**

Navigate to `http://localhost:8000`. Verify, capturing a screenshot at each:
1. Page loads; result count shows the full corpus ("Showing … of N").
2. Left facet rail renders with counts (Region default-open).
3. Checking a Region facet narrows results and counts update.
4. Clicking **Details** on a card expands and shows body text (confirms lazy `data/records/<id>.json` fetch — check the network panel for the request).
5. Typing a word that only appears in a body (e.g. a term from a regulation's text, not its title) returns that record after a moment (confirms MiniSearch warmed).
6. Dark-mode toggle and "Copy link" still work; reload preserves URL state.

- [ ] **Step 3: Record results**

Note any failures. If all pass, Phase 1 is functionally complete (UI unchanged, now data-driven).

- [ ] **Step 4: Stop the server** (Ctrl+C in that terminal).

---

## Self-review checklist (run before handing off to execution)

- **Spec coverage:** Phase 1 of the spec = "Split inline HTML into shell + css + js; emit index.json, per-record bodies, taxonomy.json, search index; client router + lazy body fetch; preserve current results behavior; validate search-index size budget." Tasks 1–9 cover each; the client *router* (Home vs Workspace) is intentionally deferred to Phase 2 since Phase 1 keeps the single existing view — call this out to the executor.
- **No regressions to data:** This plan never writes `regulations/*.md`; it only reads them. Safe to run alongside the `chore/auto-tag-backlog` agent.
- **Windows/OneDrive:** `build()` keeps using the existing `_list_md_files` PowerShell fallback — do not remove it.

## Execution handoff

After this plan is approved, Phase 2 (Home view) and Phase 3 (Workspace) get their own plans, written against the same spec once Phase 1 lands and the search-index size is known.
