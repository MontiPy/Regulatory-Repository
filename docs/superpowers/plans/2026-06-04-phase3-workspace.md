# Phase 3 — Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the Workspace (results view) to fix the four research-flagged friction points and add a side reading pane: removable **filter chips**, the availability bar **folded into the rail**, **tiered facets** (primary vs. "More"), **results grouped by market** when an area is selected, and a **URL-addressable side reading pane** replacing expand-in-place.

**Architecture:** Evolve the existing `assets/app.js` Workspace. The `.layout` becomes `filters | results | reading-pane`. `render()` gains optional market grouping. Expand-in-place is replaced by a reading pane keyed on `?id=` and integrated with the Phase 2 router. The "Show" availability bar is removed from the header and rendered as an "Availability" section inside the filter rail under a "More filters" disclosure. No build/data changes — `taxonomy.json` (incl. `region_series`) and lazy `records/<id>.json` already provide everything.

**Tech Stack:** Vanilla JS + the existing CSS tokens. No JS test runner — JS tasks verified by `node --check` + a scripted Playwright MCP smoke test (Task 7).

---

## Spec references
Implements §8 (Workspace) + §10 (coverage behaviors) of
`docs/superpowers/specs/2026-06-04-regulatory-tool-ux-redesign-design.md`. Reading approach is the
approved **Option Y (side reading pane)**.

## Current state (what we modify)
`assets/app.js` (on `main`) Workspace pieces: `render()`, `cardTemplate()`, `expandedContent()`, the
`cards` click handler (currently toggles `expanded` + lazy-fetches body), `buildFilters()`,
`getVisibleRecords()`, availability (`availBoxes`, `selectedAvailability`, `AVAIL_CATEGORIES`),
`applyUrlParams()`/`syncUrl()`, and the Phase 2 router (`route`, `workspaceActive`, `workspaceEls`).
Template `.view-bar` (availability) is in the header; `.layout` = `aside.filters` + `main`.

## File structure
| File | Responsibility |
|---|---|
| `templates/index.html.j2` | Remove `.view-bar`; add a chip bar in `main`; add a reading-pane `<aside id="reader">` in `.layout`. |
| `assets/styles.css` | Chip bar, "More filters" disclosure, group headers, reading-pane (wide split + mobile full-screen), rail-collapsed-when-reading. |
| `assets/app.js` | `renderChips()`, availability-in-rail, tiered `buildFilters()`, grouped `render()`, reading-pane open/close + `?id=` routing (replacing expand-in-place). |

`app.js` grows; if it passes ~750 lines and feels unwieldy after this phase, a follow-up split is reasonable — but do not split mid-phase.

---

## Task 1: Active filter chips bar

**Files:** `templates/index.html.j2`, `assets/styles.css`, `assets/app.js`. Verify: `node --check` + browser (Task 7).

- [ ] **Step 1: Add the chip bar to the template**

In `templates/index.html.j2`, inside `<main>`, insert a chip bar BETWEEN the `filters-toggle` button and `#result-count`:
```html
      <button type="button" class="filters-toggle" id="filters-toggle" aria-expanded="false">Filters</button>
      <div class="chip-bar hidden" id="chip-bar" aria-label="Active filters"></div>
      <p id="result-count" aria-live="polite">Showing 0 of 0</p>
```

- [ ] **Step 2: Add chip CSS**

Append to `assets/styles.css`:
```css
/* ── Active filter chips ───────────────────────────────────── */
.chip-bar { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 0 0 14px; }
.chip-bar.hidden { display: none; }
.active-chip { display: inline-flex; align-items: center; gap: 6px; height: 24px; padding: 0 6px 0 9px; border: 1px solid rgba(204,0,0,0.30); background: var(--red-0); color: var(--honda-red); font-size: 12px; }
html[data-theme="dark"] .active-chip { background: var(--filter-active-bg); }
.active-chip .chip-x { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; border: none; background: none; color: inherit; cursor: pointer; font-size: 14px; line-height: 1; padding: 0; }
.active-chip .chip-x:hover { color: var(--red-7); }
.chip-clear-all { background: none; border: none; color: var(--fg-3); cursor: pointer; font-size: 12px; text-decoration: underline; padding: 0 4px; }
.chip-clear-all:hover { color: var(--honda-red); }
```

- [ ] **Step 3: Implement `renderChips()` in app.js**

The function reads the active search query + facet selections + non-default availability and renders removable chips. `FILTERS`, `readSelections`, `displayLabel`, `escapeHtml`, `searchInput`, `selectedAvailability`, `AVAIL_CATEGORIES` already exist. Add near `render`:
```js
    const AVAIL_LABELS = { full: "Full text", paywall: "Paywall", noconn: "No live connection" };

    function renderChips() {
      const bar = document.querySelector("#chip-bar");
      const chips = [];
      const q = searchInput.value.trim();
      if (q) chips.push({ type: "q", label: `Search: "${q}"` });
      const sel = readSelections();
      FILTERS.forEach((f) => {
        Array.from(sel[f.key]).forEach((v) => {
          chips.push({ type: "facet", key: f.key, value: v, label: `${f.label}: ${displayLabel(v)}` });
        });
      });
      // Availability only when it differs from the default (full only).
      const shown = AVAIL_CATEGORIES.filter((c) => selectedAvailability().has(c));
      const isDefault = shown.length === 1 && shown[0] === "full";
      if (!isDefault) {
        shown.forEach((c) => chips.push({ type: "avail", value: c, label: `Show: ${AVAIL_LABELS[c]}` }));
      }
      if (chips.length === 0) { bar.classList.add("hidden"); bar.innerHTML = ""; return; }
      bar.classList.remove("hidden");
      bar.innerHTML = chips.map((c) =>
        `<span class="active-chip" data-chip-type="${c.type}"${c.key ? ` data-chip-key="${escapeHtml(c.key)}"` : ""}${c.value !== undefined ? ` data-chip-value="${escapeHtml(c.value)}"` : ""}>`
        + `${escapeHtml(c.label)}<button type="button" class="chip-x" aria-label="Remove">×</button></span>`
      ).join("") + `<button type="button" class="chip-clear-all" id="chip-clear-all">Clear all</button>`;
    }
```

- [ ] **Step 4: Call `renderChips()` from `render()`**

In `render()`, add `renderChips();` as the last line (after `updateFacetCounts(visible);`).

- [ ] **Step 5: Handle chip removal**

Add a click listener (near the other listeners):
```js
    document.querySelector("#chip-bar").addEventListener("click", (event) => {
      if (event.target.closest("#chip-clear-all")) { clearFilters.click(); return; }
      const x = event.target.closest(".chip-x");
      if (!x) return;
      const chip = x.closest(".active-chip");
      const type = chip.dataset.chipType;
      if (type === "q") { searchInput.value = ""; }
      else if (type === "facet") {
        const el = filtersForm.querySelector(`input[name="${chip.dataset.chipKey}"][value="${CSS.escape(chip.dataset.chipValue)}"]`);
        if (el) el.checked = false;
      } else if (type === "avail") {
        const el = availBoxes.find((b) => b.dataset.avail === chip.dataset.chipValue);
        if (el) el.checked = false;
      }
      visibleLimit = PAGE_SIZE;
      render();
      syncUrl();
      updateClearButton();
      route();
    });
```

- [ ] **Step 6: Verify + commit**

Run `node --check assets/app.js` → 0. Then:
```bash
git add templates/index.html.j2 assets/styles.css assets/app.js
git commit -m "feat(workspace): removable active-filter chips bar"
```

---

## Task 2: Fold availability into the filter rail

**Files:** `templates/index.html.j2`, `assets/app.js`, `assets/styles.css`. Verify: `node --check` + browser.

Goal: remove the header `.view-bar` and render the three availability checkboxes as a rail section, so there is ONE filter model. The existing IDs (`avail-full` etc.) and `data-avail` attributes are preserved so `availBoxes`, `selectedAvailability`, `applyUrlParams`, and `syncUrl` keep working unchanged — we just relocate the inputs.

- [ ] **Step 1: Remove the `.view-bar` from the template**

Delete the entire `<div class="view-bar" ...> ... </div>` block (lines 31–45 of the current template). The header now ends after `</div>` (header-inner) and `</header>`.

- [ ] **Step 2: Add an Availability section container to the rail**

In the template, inside `<form id="filters-form"></form>` is dynamically built. Instead, add a STATIC availability section ABOVE the form, inside `.filters-inner`, after the `clear-button`:
```html
        <button type="button" class="clear-button hidden" id="clear-filters">Clear all filters</button>
        <details class="avail-section" open>
          <summary>Availability</summary>
          <div class="facet-options" id="avail-options">
            <label class="facet-option"><input type="checkbox" id="avail-full" data-avail="full" checked><span>Full text</span></label>
            <label class="facet-option"><input type="checkbox" id="avail-paywall" data-avail="paywall"><span>Paywall</span></label>
            <label class="facet-option"><input type="checkbox" id="avail-noconn" data-avail="noconn"><span>No live connection</span></label>
          </div>
        </details>
        <form id="filters-form"></form>
```
The `id`/`data-avail` values are identical to the old view-bar inputs, so `availBoxes = Array.from(document.querySelectorAll("[data-avail]"))` still selects exactly these three.

- [ ] **Step 3: Remove `.view-bar` from the Phase 2 router**

In `assets/app.js`, `workspaceEls` currently is `[document.querySelector(".layout"), document.querySelector(".view-bar")]`. Change it to just the layout (the bar no longer exists):
```js
    const workspaceEls  = [document.querySelector(".layout")];
```

- [ ] **Step 4: Re-route + re-render on availability change (already wired in Phase 2 Task-7 fix)**

Confirm the `availBoxes` change handler ends with `render(); syncUrl(); route();` (the `route()` was added in the Phase 2 final-review fix). No change needed — just verify it's present.

- [ ] **Step 5: Style the availability section like other rail sections**

The availability section reuses the existing `details`/`summary`/`facet-option` rail styles (including the red-tick `summary::before`). Append only the section border to `assets/styles.css`:
```css
.avail-section { border-bottom: 1px solid var(--line-1); }
```

- [ ] **Step 6: Verify + commit**

`node --check assets/app.js` → 0. Build and confirm no `view-bar` remains: `python scripts/build.py --draft && python -c "print('view-bar' not in open('dist/index.html',encoding='utf-8').read())"` → True.
```bash
git add templates/index.html.j2 assets/app.js assets/styles.css
git commit -m "feat(workspace): fold availability into the filter rail"
```

---

## Task 3: Tiered facets (primary vs. More filters)

**Files:** `assets/app.js`. Verify: `node --check` + browser.

`buildFilters()` renders all FILTERS as a flat list. Split into primary (Region, System, Commodity) always shown, and secondary (Status, Tagging Status, Translation) inside a "More filters" disclosure.

- [ ] **Step 1: Add a primary/secondary partition**

Near the `FILTERS` array, add:
```js
    const PRIMARY_FILTERS = new Set(["region", "systems", "commodities"]);
```

- [ ] **Step 2: Rework `buildFilters()` to render two groups**

Replace the body of `buildFilters()` so it builds primary sections directly and wraps secondary sections in a `<details class="more-filters">`. The existing per-filter section markup is factored into a local helper:
```js
    function buildFilters() {
      const DEFAULT_OPEN = new Set(["region"]);
      function sectionHtml(filter) {
        const options = (TAXONOMY[filter.taxonomyKey] || [])
          .filter((value) => (CORPUS_COUNTS[filter.key]?.[value] || 0) > 0)
          .sort((a, b) => (CORPUS_COUNTS[filter.key][b] || 0) - (CORPUS_COUNTS[filter.key][a] || 0));
        if (options.length < 2) return "";
        const controls = options.map((value) => {
          const id = `${filter.key}-${slug(value)}`;
          return `
            <label class="facet-option" for="${escapeHtml(id)}">
              <input type="checkbox" id="${escapeHtml(id)}" name="${escapeHtml(filter.key)}" value="${escapeHtml(value)}">
              <span>${escapeHtml(displayLabel(value))}</span>
              <span class="facet-count" data-facet="${escapeHtml(filter.key)}" data-value="${escapeHtml(value)}" aria-hidden="true">0</span>
            </label>`;
        }).join("");
        const infoIcon = filter.tooltip ? `<span class="filter-info" data-tooltip="${escapeHtml(filter.tooltip)}">i</span>` : "";
        return `
          <details${DEFAULT_OPEN.has(filter.key) ? " open" : ""}>
            <summary>${escapeHtml(filter.label)}${infoIcon}</summary>
            <div class="facet-options collapsed" data-facet="${escapeHtml(filter.key)}">${controls}</div>
            <button type="button" class="facet-more" data-more="${escapeHtml(filter.key)}"></button>
          </details>`;
      }
      const primary = FILTERS.filter((f) => PRIMARY_FILTERS.has(f.key)).map(sectionHtml).join("");
      const secondary = FILTERS.filter((f) => !PRIMARY_FILTERS.has(f.key)).map(sectionHtml).join("");
      filtersForm.innerHTML = primary
        + (secondary.trim()
            ? `<details class="more-filters"><summary>More filters</summary><div>${secondary}</div></details>`
            : "");
    }
```
(This is the same section markup as before, only partitioned. `updateFacetCounts`, `updateFacetCollapse`, and the `facet-more` handler keep working because the `data-facet`/`data-more` attributes are unchanged.)

- [ ] **Step 3: Style the "More filters" disclosure**

Append to `assets/styles.css`:
```css
.more-filters > summary { color: var(--fg-3); }
.more-filters[open] > summary { color: var(--fg-1); }
.more-filters > div { border-top: 1px solid var(--line-1); }
```

- [ ] **Step 4: Verify + commit**

`node --check assets/app.js` → 0.
```bash
git add assets/app.js assets/styles.css
git commit -m "feat(workspace): tier facets into primary and More filters"
```

---

## Task 4: Group results by market when an area is selected

**Files:** `assets/app.js`, `assets/styles.css`. Verify: `node --check` + browser.

When a System or Commodity facet is active (the journey-A case), group the visible records by region with headers `United States · FMVSS (N)`. Otherwise render the flat list as today.

- [ ] **Step 1: Add a market-group renderer**

Add near `render`:
```js
    function regionGroupLabel(region) {
      const meta = (TAXONOMY.region_series || {})[region];
      if (meta && meta.series) return `${meta.name || region} · ${meta.series}`;
      return (meta && meta.name) || region;
    }

    function areaSelected() {
      const sel = readSelections();
      return sel.systems.size > 0 || sel.commodities.size > 0;
    }

    function renderGrouped(renderable) {
      const groups = new Map();
      renderable.forEach((r) => {
        if (!groups.has(r.region)) groups.set(r.region, []);
        groups.get(r.region).push(r);
      });
      const order = Array.from(groups.keys()).sort((a, b) => groups.get(b).length - groups.get(a).length);
      return order.map((region) => {
        const recs = groups.get(region);
        return `<div class="market-group"><h3 class="market-group-head">${escapeHtml(regionGroupLabel(region))} <span class="market-group-count">(${recs.length})</span></h3>`
          + recs.map(cardTemplate).join("") + `</div>`;
      }).join("");
    }
```

- [ ] **Step 2: Use grouping in `render()`**

In `render()`, the line that sets `cards.innerHTML` currently is:
```js
      cards.innerHTML = renderable.length
        ? renderable.map(cardTemplate).join("")
        : '<div class="empty-state">No regulations match the current filters.</div>';
```
Replace with:
```js
      cards.innerHTML = renderable.length
        ? (areaSelected() ? renderGrouped(renderable) : renderable.map(cardTemplate).join(""))
        : '<div class="empty-state">No regulations match the current filters.</div>';
```

- [ ] **Step 3: Style group headers**

Append to `assets/styles.css`:
```css
.market-group { margin-bottom: 8px; }
.market-group-head { font-size: 12px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-2); margin: 14px 0 8px; padding-bottom: 6px; border-bottom: 1px solid var(--line-1); }
.market-group-count { color: var(--fg-3); font-weight: 400; }
.market-group .reg-card { margin-bottom: 12px; }
```

- [ ] **Step 4: Verify + commit**

`node --check assets/app.js` → 0.
```bash
git add assets/app.js assets/styles.css
git commit -m "feat(workspace): group results by market when an area is selected"
```

---

## Task 5: Reading-pane markup + styles

**Files:** `templates/index.html.j2`, `assets/styles.css`. Verify: build + browser.

- [ ] **Step 1: Add the reading-pane aside to the layout**

In the template `.layout`, AFTER `<main> ... </main>` and before the closing `</div>`, add:
```html
    <aside class="reader hidden" id="reader" aria-label="Regulation reader">
      <div class="reader-head">
        <strong class="reader-title" id="reader-title"></strong>
        <button type="button" class="reader-close" id="reader-close" aria-label="Close reader">×</button>
      </div>
      <div class="reader-body" id="reader-body"></div>
    </aside>
```

- [ ] **Step 2: Reading-pane CSS (wide split + mobile full-screen + rail collapse)**

Append to `assets/styles.css`:
```css
/* ── Reading pane ──────────────────────────────────────────── */
.layout.reading { grid-template-columns: 264px minmax(0, 1.3fr) minmax(360px, 1.1fr); }
.layout.reading .filters { display: none; }           /* collapse rail to give the reader room */
.reader { border-left: 1px solid var(--line-1); background: var(--surface); display: flex; flex-direction: column; min-height: calc(100vh - 75px); }
.reader.hidden { display: none; }
.reader-head { position: sticky; top: 0; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 18px; border-bottom: 1px solid var(--line-1); background: var(--bg-2); }
.reader-title { font-size: 14px; font-weight: 900; color: var(--fg-1); }
.reader-close { background: none; border: none; font-size: 22px; line-height: 1; color: var(--fg-3); cursor: pointer; padding: 0 4px; }
.reader-close:hover { color: var(--honda-red); }
.reader-body { padding: 18px; overflow-y: auto; font-size: 14px; color: var(--fg-1); }
@media (max-width: 1000px) {
  .layout.reading { grid-template-columns: 1fr; }
  .layout.reading .filters { display: none; }
  .reader { position: fixed; inset: 75px 0 0 0; z-index: 30; border-left: none; }
}
```

- [ ] **Step 3: Build + confirm markup present**

`python scripts/build.py --draft` then `python -c "t=open('dist/index.html',encoding='utf-8').read(); print('reader' in t and 'reader-body' in t and 'reader-close' in t)"` → True.

- [ ] **Step 4: Commit**

```bash
git add templates/index.html.j2 assets/styles.css
git commit -m "feat(workspace): reading-pane markup and styles"
```

---

## Task 6: Reading pane — open/close, lazy body, ?id= routing (replaces expand-in-place)

**Files:** `assets/app.js`. Verify: `node --check` + browser.

This replaces the expand-in-place behavior. Cards get a "Read" button; clicking opens the pane with the lazily-fetched body + metadata + equivalents (only when present), sets `?id=`, collapses the rail. Close clears `?id=`. Deep links to `?id=` open the pane on load.

- [ ] **Step 1: Simplify `cardTemplate` to a non-expanding card with a Read button**

The current `cardTemplate` conditionally renders `expandedContent`. Replace it with a card whose button opens the reader. The new `cardTemplate`:
```js
    function cardTemplate(record) {
      const q = searchInput.value;
      const isActive = record.id === openReaderId;
      const statusBadge = record.status && record.status !== "in-force"
        ? `<span class="badge ${statusClass(record.status)}">${escapeHtml(displayLabel(record.status))}</span>` : "";
      return `
        <article class="reg-card${isActive ? " is-reading" : ""}" id="reg-${slug(record.id)}">
          <div class="card-top">
            <div>
              <h2 class="reg-title">${highlight(record.title || record.id, q)}</h2>
              <div class="badges">
                <span class="badge region">${escapeHtml(record.region)}</span>
                <span class="badge">${escapeHtml(record.citation)}</span>
                ${statusBadge}
              </div>
              <p class="summary">${highlight(record.summary_text || "No summary available.", q)}</p>
            </div>
            <button type="button" class="expand-button" data-read="${escapeHtml(record.id)}" aria-expanded="${isActive}">
              ${isActive ? "Reading" : "Read"}
            </button>
          </div>
        </article>`;
    }
```
Add module state near the top: `let openReaderId = null;`. Add a `.reg-card.is-reading { border-left: 3px solid var(--honda-red); padding-left: 17px; }` rule to `assets/styles.css` in this task's commit.

- [ ] **Step 2: Build the reader body (reuse the existing meta/equivalents helpers)**

The existing `expandedContent(record)` builds the body + meta panel. Rename/repurpose it as `readerBodyHtml(record)` returning the inner HTML for the pane (it already references `bodyCache`, `facetChips`, `relatedLinks`, `stubBanner`, `hostLabel`). Keep its existing internals; just ensure equivalents/related render only when present (the existing `facetChips`/`relatedLinks` already return "" for empty arrays — confirm). Add this opener:
```js
    async function openReader(id) {
      const record = recordById.get(id);
      if (!record) return;
      openReaderId = id;
      if (!bodyCache.has(id)) {
        try {
          const data = await fetch(`data/records/${encodeURIComponent(id)}.json`).then((r) => r.json());
          bodyCache.set(id, data.body_html || "");
        } catch { bodyCache.set(id, "<p>Failed to load regulation text.</p>"); }
      }
      document.querySelector("#reader-title").textContent = record.title || record.id;
      document.querySelector("#reader-body").innerHTML = readerBodyHtml(record);
      document.querySelector("#reader").classList.remove("hidden");
      document.querySelector(".layout").classList.add("reading");
      render();              // re-mark the active card
      syncUrl();             // adds ?id=
    }

    function closeReader() {
      openReaderId = null;
      document.querySelector("#reader").classList.add("hidden");
      document.querySelector(".layout").classList.remove("reading");
      render();
      syncUrl();
    }
```

- [ ] **Step 3: Replace the `cards` click handler**

The current `cards` click handler toggles `expanded` and lazy-fetches. Replace its body with:
```js
    cards.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-read]");
      if (!btn) return;
      const id = btn.getAttribute("data-read");
      if (id === openReaderId) closeReader(); else openReader(id);
    });
```
Add the close-button listener:
```js
    document.querySelector("#reader-close").addEventListener("click", closeReader);
```
Remove the now-unused `expanded` Set and any references to it in `cardTemplate` (handled in Step 1). Leave `bodyCache` (still used).

- [ ] **Step 4: Persist the reader in the URL (`?id=`)**

In `syncUrl()`, after the existing params are appended and before `history.replaceState`, add the id:
```js
        if (openReaderId) params.set("id", openReaderId);
```
In `applyUrlParams()`, at the end, read it back (open the pane on deep-link/back). Add:
```js
      const idParam = params.get("id");
      if (idParam && recordById.get(idParam)) { openReader(idParam); }
      else if (!idParam && openReaderId) { closeReader(); }
```
Note: `openReader` is async but `applyUrlParams` need not await it. Because `?id=` is a workspace-implying param, also add to `workspaceActive()`: `if (new URLSearchParams(window.location.search).get("id")) return true;` — add it right after the `view === "results"` check.

- [ ] **Step 5: Verify + commit**

`node --check assets/app.js` → 0.
```bash
git add assets/app.js assets/styles.css
git commit -m "feat(workspace): side reading pane with ?id= routing (replaces expand-in-place)"
```

---

## Task 7: Browser smoke test (Playwright MCP)

**Files:** none.

- [ ] **Step 1: Build + serve**: `python scripts/build.py --draft` then `python -m http.server 8139 --directory dist`.

- [ ] **Step 2: Verify (screenshot each):**
1. **Chips:** apply Region=US + a System; two removable chips appear; clicking a chip's × removes that filter and updates results; "Clear all" empties them.
2. **Availability in rail:** the header "Show" bar is gone; an "Availability" section is in the rail with Full text / Paywall / No live connection; toggling Paywall adds a chip and changes results.
3. **Tiered facets:** Region/System/Commodity are top-level; Status/Tagging/Translation are inside a "More filters" disclosure.
4. **Group by market:** selecting a System (e.g. Crashworthiness) groups results under market headers like "United States · FMVSS (N)"; with no area selected, the list is flat.
5. **Reading pane:** clicking "Read" opens the right-hand pane with the regulation body (confirm `data/records/<id>.json` fetch in the network panel), the rail collapses, the card shows "Reading"; the URL gains `?id=`. Close (×) hides the pane and clears `?id=`.
6. **Deep link:** navigate directly to `?id=us-fmvss-208` → the pane opens on load with that regulation.
7. **Equivalents:** confirm the reader's "Equivalents & Related" only appears for records that have them (most won't today — that's expected).
8. **Mobile:** at ~800px width, the reading pane is full-screen over the list.

- [ ] **Step 3: Record results; stop the server.**

---

## Self-review checklist (run before execution)
- **Spec §8 coverage:** chips (T1), folded availability (T2), tiered facets (T3), group-by-market (T4), side reading pane + `?id=` (T5–T6). ✓
- **Coverage §10:** untagged still reachable (search + Region + availability section); reading pane shows equivalents only when present. ✓
- **Router integration:** `workspaceActive()` updated for `?id=`; `.view-bar` removed from `workspaceEls`. ✓
- **No data/build changes:** all from existing `taxonomy.json` (region_series) + lazy bodies. ✓
- **Removed cleanly:** expand-in-place (`expanded` Set, `expandedContent` inline render) replaced by the reader; confirm no dangling references.

## Execution handoff
Phase 3 completes the redesign. After it lands, consider the deferred data tracks in `TODO.md`
(populate `un_equivalent`/`related` to light up the reader's equivalents; finish the 26 untagged
records; EU/long-tail series labels) and a refresh of the stale `README.md` counts.
