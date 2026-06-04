# Phase 2 — Home View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a coverage-aware **Home** front door (search + Browse-by-System/Commodity/Market directories) in front of the existing results view, with a tiny URL router that shows Home on a bare URL and the Workspace (current results UI) once a search/facet is active.

**Architecture:** Evolve the single-page app from Phase 1. The shell gains a hidden `<section id="home">`; `app.js` gains a `route()` function that toggles `#home` vs the existing `.layout`/`.view-bar` based on URL params. `renderHome()` builds the directory from the already-loaded `CORPUS_COUNTS` (systems/commodities/regions) and `TAXONOMY.region_series` (emitted by Phase 1). Clicking a tile or searching navigates into the Workspace pre-filtered by reusing the existing `applyUrlParams()` + `render()`. No build/data changes — Phase 1 already emits everything Home needs.

**Tech Stack:** Vanilla JS + the existing CSS token system in `assets/styles.css`. No JS test runner exists, so JS tasks are verified by `node --check` + a scripted Playwright MCP smoke test (Task 7). Light-mode default and `Ctrl+K` are spec decisions realized here.

---

## Spec references
This plan implements §7 (Home view) and the Home-related rows of §5 of
`docs/superpowers/specs/2026-06-04-regulatory-tool-ux-redesign-design.md`:
search-led hero + coverage line; Browse-by-System/Commodity (A–Z default, Count toggle, Top-N + more);
Browse-by-Market (Count default, A–Z toggle, `Series (Region)` long-name tiles); tile→Workspace drill-in;
light-mode default; Windows `Ctrl+K`.

## Out of scope (Phase 3)
Filter chips, group-by-market results, side reading pane, folded availability bar, tiered facets. Phase 2
keeps the Workspace results UI exactly as Phase 1 left it.

## File structure

| File | Responsibility |
|---|---|
| `templates/index.html.j2` (modify) | Add a `<section id="home" class="home hidden">…</section>` between the header and `.layout`; add a home mount structure (hero, three directory panels). The header title becomes a Home link. |
| `assets/styles.css` (modify) | Add `.home`, hero, `.dir-panel`, `.dir-tile`, `.dir-sort`, `.coverage-line` rules using existing tokens. |
| `assets/app.js` (modify) | Add `route()`, `renderHome()`, sort state, tile/search navigation, light-mode default, `Ctrl+K`. Hook `route()` into `boot()` and into navigation. |

`app.js` will grow ~150 lines. If it exceeds ~700 lines and feels unwieldy, that's acceptable for Phase 2; a split into `home.js` can be considered in Phase 3 when the Workspace is also reworked. Do NOT split it in this phase.

---

## Task 1: Light-mode default + Ctrl+K shortcut

**Files:** Modify `assets/app.js` (the theme IIFE at the end, and the keydown handler). Verify: `node --check` + Playwright in Task 7.

- [ ] **Step 1: Default theme to light**

In the theme IIFE near the end of `app.js`, the line currently reads:
```js
      applyTheme(localStorage.getItem("theme") || systemTheme());
```
Change it to default to light when the user has no saved preference (spec decision — light is the default, not system):
```js
      applyTheme(localStorage.getItem("theme") || "light");
```
Leave `systemTheme()` defined (it's harmless) — only the default changes.

- [ ] **Step 2: Add Ctrl+K (and keep "/") to focus search**

The existing keydown handler is:
```js
    document.addEventListener("keydown", (event) => {
      const target = event.target;
      const isTyping = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target.isContentEditable;
      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        searchInput.focus();
      }
    });
```
Replace the `if` block with one that also handles Ctrl+K / Cmd+K (Windows-first, but Cmd kept for Macs):
```js
      if ((event.key === "k" || event.key === "K") && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        searchInput.focus();
        searchInput.select();
        return;
      }
      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        searchInput.focus();
      }
```

- [ ] **Step 3: Verify syntax**

Run: `node --check assets/app.js`
Expected: exit 0, no output.

- [ ] **Step 4: Commit**

```bash
git add assets/app.js
git commit -m "feat(home): light-mode default and Ctrl+K search shortcut"
```

---

## Task 2: Home markup in the shell + base styles

**Files:** Modify `templates/index.html.j2`, `assets/styles.css`. Verify: build + Playwright (Task 7).

- [ ] **Step 1: Add the Home section to the template**

In `templates/index.html.j2`, immediately AFTER the closing `</header>` and BEFORE `<div class="layout">`, insert:
```html
  <section id="home" class="home hidden" aria-label="Home">
    <div class="home-hero">
      <h1 class="home-title">Which regulations apply to your part, system, or market?</h1>
      <p class="coverage-line" id="coverage-line"></p>
    </div>
    <div class="home-panels">
      <section class="dir-panel" data-panel="systems">
        <div class="dir-head"><span class="dir-label">Browse by System</span><span class="dir-sort" data-sort-for="systems"></span></div>
        <div class="dir-tiles" data-tiles="systems"></div>
        <button type="button" class="dir-more hidden" data-more-for="systems"></button>
      </section>
      <section class="dir-panel" data-panel="commodities">
        <div class="dir-head"><span class="dir-label">Browse by Commodity</span><span class="dir-sort" data-sort-for="commodities"></span></div>
        <div class="dir-tiles" data-tiles="commodities"></div>
        <button type="button" class="dir-more hidden" data-more-for="commodities"></button>
      </section>
    </div>
    <section class="dir-panel dir-panel-market" data-panel="region">
      <div class="dir-head"><span class="dir-label">Browse by Market</span><span class="dir-sort" data-sort-for="region"></span></div>
      <div class="dir-tiles" data-tiles="region"></div>
      <button type="button" class="dir-more hidden" data-more-for="region"></button>
    </section>
  </section>
```

- [ ] **Step 2: Make the header title a Home link**

In the template header, the title is currently:
```html
        <span class="header-title">Regulatory Repository</span>
```
Change it to a button so it can route Home (keep styling by reusing the class):
```html
        <button type="button" class="header-title" id="home-link">Regulatory Repository</button>
```

- [ ] **Step 3: Add Home styles to `assets/styles.css`**

Append these rules at the end of `assets/styles.css` (they reuse existing tokens):
```css
/* ── Home view ─────────────────────────────────────────────── */
.home { padding: 28px; max-width: 1100px; margin: 0 auto; }
.home-hero { text-align: center; padding: 12px 0 20px; }
.home-title { font-size: 22px; font-weight: 900; letter-spacing: 0.01em; margin: 0 0 12px; color: var(--fg-1); }
.coverage-line { font-size: 13px; color: var(--fg-3); margin: 0; }
.coverage-line a { color: var(--honda-red); }
.home-panels { display: grid; gap: 18px; grid-template-columns: 1fr; }
@media (min-width: 820px) { .home-panels { grid-template-columns: 1fr 1fr; } }
.dir-panel { border: 1px solid var(--line-1); background: var(--surface); padding: 16px; margin-top: 18px; }
.home-panels .dir-panel { margin-top: 0; }
.dir-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.dir-label { font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--fg-2); border-left: 3px solid var(--honda-red); padding-left: 8px; }
.dir-sort { font-size: 11px; color: var(--fg-3); }
.dir-sort button { background: none; border: none; cursor: pointer; color: var(--fg-3); font: inherit; padding: 0 2px; }
.dir-sort button.active { color: var(--honda-red); font-weight: 700; }
.dir-tiles { display: flex; flex-wrap: wrap; gap: 6px; }
.dir-tile { display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 10px; border: 1px solid var(--line-1); background: var(--bg-2); color: var(--fg-1); font-size: 12px; cursor: pointer; transition: border-color var(--dur) var(--ease), background var(--dur) var(--ease); }
.dir-tile:hover { border-color: var(--honda-red); background: var(--red-0); }
.dir-tile .dir-count { color: var(--fg-3); font-variant-numeric: tabular-nums; }
.dir-more { margin-top: 10px; background: none; border: none; color: var(--honda-red); cursor: pointer; font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 0; }
.dir-more:hover { text-decoration: underline; }
html[data-theme="dark"] .dir-tile:hover { background: var(--filter-active-bg); }
```

- [ ] **Step 4: Build and confirm the shell carries the new markup**

Run: `python scripts/build.py --draft`
Then: `python -c "t=open('dist/index.html',encoding='utf-8').read(); print('home section:', 'id=\"home\"' in t); print('home-link:', 'id=\"home-link\"' in t); print('tiles mount:', 'data-tiles=\"systems\"' in t)"`
Expected: all `True`.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html.j2 assets/styles.css
git commit -m "feat(home): home section markup and styles in shell"
```

---

## Task 3: Router — show Home vs Workspace from the URL

**Files:** Modify `assets/app.js`. Verify: `node --check` + Playwright (Task 7).

The Workspace is "active" when there is a search query OR any facet/avail param in the URL. A bare URL (or `?view=home`) shows Home.

- [ ] **Step 1: Add element handles and a `route()` function**

Near the other `document.querySelector` handles at the top of `app.js`, add:
```js
    const homeView     = document.querySelector("#home");
    const workspaceEls  = [document.querySelector(".layout"), document.querySelector(".view-bar")];
    const homeLink     = document.querySelector("#home-link");
```
Then add this function (place it near `applyUrlParams`):
```js
    function workspaceActiveFromUrl() {
      const params = new URLSearchParams(window.location.search);
      if (params.get("view") === "home") return false;
      if (params.get("view") === "results") return true;
      if ((params.get("q") || "").trim()) return true;
      if (params.has("avail")) return true;
      return FILTERS.some((f) => valuesFromParams(params, f.key).length > 0);
    }

    function route() {
      const onWorkspace = workspaceActiveFromUrl();
      homeView.classList.toggle("hidden", onWorkspace);
      workspaceEls.forEach((el) => el && el.classList.toggle("hidden", !onWorkspace));
      if (!onWorkspace) renderHome();
    }
```

- [ ] **Step 2: Provide a temporary `renderHome` stub so route() runs**

Add a stub now (replaced fully in Task 4) so `node --check` and the router work in isolation:
```js
    function renderHome() { /* populated in Task 4 */ }
```

- [ ] **Step 3: Call `route()` at the end of `boot()`**

In `boot()`, after `updateClearButton();` and before the search-warm line, add `route();`:
```js
      render();
      updateClearButton();
      route();
      if (typeof requestIdleCallback === "function") { requestIdleCallback(loadSearch); }
```

- [ ] **Step 4: Home link navigates Home**

Add near the other listeners:
```js
    homeLink.addEventListener("click", () => {
      history.replaceState(null, "", window.location.pathname);
      searchInput.value = "";
      filtersForm.querySelectorAll("input[type='checkbox']").forEach((el) => { el.checked = false; });
      availBoxes.forEach((b) => { b.checked = b.dataset.avail === "full"; });
      visibleLimit = PAGE_SIZE;
      route();
      updateClearButton();
    });
```

- [ ] **Step 5: Re-route after searches and filter changes**

The Workspace becomes active when the user types or checks a facet. In the existing `searchInput` `input` listener and the `filtersForm` `change` listener, add a `route()` call after `syncUrl()` so the view switches when a query/facet first appears (and back to Home when cleared). In BOTH listeners change:
```js
      render();
      syncUrl();
      updateClearButton();
```
to:
```js
      render();
      syncUrl();
      updateClearButton();
      route();
```
Also add `route()` at the end of the `clearFilters` click handler (after `updateClearButton();`) so clearing everything returns to Home.

- [ ] **Step 6: Verify syntax**

Run: `node --check assets/app.js`
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add assets/app.js
git commit -m "feat(home): URL router toggling Home and Workspace"
```

---

## Task 4: renderHome — coverage line + directory tiles

**Files:** Modify `assets/app.js`. Verify: `node --check` + Playwright (Task 7).

`CORPUS_COUNTS` (built in `rebuildCorpusCounts`) already holds per-value counts for `systems`, `commodities`, and `region`. `TAXONOMY.region_series` maps region → `{series, name}`.

- [ ] **Step 1: Add sort state and helpers**

Near the top state declarations add:
```js
    const homeSort = { systems: "az", commodities: "az", region: "count" };
    const homeShowAll = { systems: false, commodities: false, region: false };
    const HOME_TOP_N = 14;
```
Add a label helper for market tiles (Series (Region)):
```js
    function marketTileLabel(region) {
      const meta = (TAXONOMY.region_series || {})[region];
      if (meta && meta.series) return `${meta.series} (${meta.name || region})`;
      if (meta && meta.name) return meta.name;
      return region;
    }
```

- [ ] **Step 2: Replace the `renderHome` stub with the real implementation**

```js
    function renderHome() {
      // Coverage line
      const total = REGS.length;
      const tagged = (CORPUS_COUNTS.tagging_status?.["llm-tagged"]) || 0;
      const untagged = (CORPUS_COUNTS.tagging_status?.["untagged"]) || 0;
      const cov = document.querySelector("#coverage-line");
      cov.innerHTML = `${tagged} of ${total} classified by part &amp; system · `
        + `<a href="?view=results" data-browse-all>browse all ${total} by market</a>`
        + (untagged ? ` · ${untagged} untagged` : "");

      renderDirPanel("systems", (v) => displayLabel(v));
      renderDirPanel("commodities", (v) => displayLabel(v));
      renderDirPanel("region", (v) => marketTileLabel(v));
    }

    function renderDirPanel(key, labelFn) {
      const counts = CORPUS_COUNTS[key] || {};
      let values = Object.keys(counts).filter((v) => counts[v] > 0);
      if (homeSort[key] === "az") {
        values.sort((a, b) => labelFn(a).localeCompare(labelFn(b)));
      } else {
        values.sort((a, b) => counts[b] - counts[a]);
      }
      const showAll = homeShowAll[key];
      const shown = showAll ? values : values.slice(0, HOME_TOP_N);
      const tiles = shown.map((v) =>
        `<button type="button" class="dir-tile" data-dir-key="${escapeHtml(key)}" data-dir-value="${escapeHtml(v)}">`
        + `<span>${escapeHtml(labelFn(v))}</span><span class="dir-count">${counts[v]}</span></button>`
      ).join("");
      document.querySelector(`[data-tiles="${key}"]`).innerHTML = tiles;

      // Sort toggle (A–Z | Count) with current selection highlighted
      const sortEl = document.querySelector(`[data-sort-for="${key}"]`);
      const az = homeSort[key] === "az";
      sortEl.innerHTML = `Sort: `
        + `<button data-set-sort="${key}" data-sort="az" class="${az ? "active" : ""}">A–Z</button> | `
        + `<button data-set-sort="${key}" data-sort="count" class="${az ? "" : "active"}">Count</button>`;

      // Show all / fewer
      const moreBtn = document.querySelector(`[data-more-for="${key}"]`);
      const hidden = values.length - shown.length;
      if (hidden > 0 || showAll) {
        moreBtn.classList.remove("hidden");
        moreBtn.textContent = showAll ? "Show fewer" : `Show all (${hidden} more)`;
      } else {
        moreBtn.classList.add("hidden");
      }
    }
```

- [ ] **Step 3: Verify syntax**

Run: `node --check assets/app.js`
Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add assets/app.js
git commit -m "feat(home): render coverage line and directory tiles"
```

---

## Task 5: Sort toggles and show-all wiring

**Files:** Modify `assets/app.js`. Verify: `node --check` + Playwright (Task 7).

- [ ] **Step 1: Delegate clicks for sort toggles and show-all inside Home**

Add one delegated listener on the Home section (place near the other listeners):
```js
    homeView.addEventListener("click", (event) => {
      const sortBtn = event.target.closest("[data-set-sort]");
      if (sortBtn) {
        homeSort[sortBtn.dataset.setSort] = sortBtn.dataset.sort;
        renderHome();
        return;
      }
      const moreBtn = event.target.closest("[data-more-for]");
      if (moreBtn) {
        const k = moreBtn.dataset.moreFor;
        homeShowAll[k] = !homeShowAll[k];
        renderHome();
        return;
      }
    });
```

- [ ] **Step 2: Verify syntax**

Run: `node --check assets/app.js`
Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add assets/app.js
git commit -m "feat(home): sort-toggle and show-all interactions"
```

---

## Task 6: Tile navigation + browse-all into the Workspace

**Files:** Modify `assets/app.js`. Verify: `node --check` + Playwright (Task 7).

- [ ] **Step 1: Add a navigation helper that enters the Workspace pre-filtered**

Add near `applyUrlParams`:
```js
    function goToWorkspace(paramKey, paramValue) {
      const params = new URLSearchParams();
      if (paramKey) params.append(paramKey, paramValue);
      history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
      applyUrlParams();   // sets the facet checkboxes / search box from the URL
      visibleLimit = PAGE_SIZE;
      route();            // workspaceActiveFromUrl() is now true -> shows Workspace
      render();
      updateClearButton();
      window.scrollTo(0, 0);
    }
```

- [ ] **Step 2: Wire tile clicks (extend the Home delegated listener from Task 5)**

In the `homeView` click listener, BEFORE the sort/more checks, add a tile handler:
```js
      const tile = event.target.closest(".dir-tile");
      if (tile) {
        goToWorkspace(tile.dataset.dirKey, tile.dataset.dirValue);
        return;
      }
      const browseAll = event.target.closest("[data-browse-all]");
      if (browseAll) {
        event.preventDefault();
        // Mark the workspace in the URL FIRST, then route, so workspaceActiveFromUrl() is true.
        history.replaceState(null, "", `${window.location.pathname}?view=results`);
        applyUrlParams();
        visibleLimit = PAGE_SIZE;
        route();
        render();
        updateClearButton();
        window.scrollTo(0, 0);
        return;
      }
```
Note: `data-dir-key` is one of `systems`/`commodities`/`region`, which are exactly the facet `name`s used by `applyUrlParams`, so the facet checkbox gets checked automatically. `?view=results` with no facets shows all records (the browse-all escape hatch).

- [ ] **Step 3: Searching from Home enters the Workspace**

This already works: the `searchInput` `input` listener calls `syncUrl()` (adds `?q=`) then `route()` (Task 3 Step 5), which flips to Workspace. No extra code. (Confirm in Task 7.)

- [ ] **Step 4: Verify syntax**

Run: `node --check assets/app.js`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add assets/app.js
git commit -m "feat(home): tile and browse-all navigation into the workspace"
```

---

## Task 7: End-to-end browser smoke test (Playwright MCP)

**Files:** none (verification only).

- [ ] **Step 1: Build and serve**

```
python scripts/build.py --draft
python -m http.server 8137 --directory dist
```

- [ ] **Step 2: Drive with Playwright MCP and verify**

Navigate to `http://localhost:8137/` and confirm, capturing a screenshot at the Home and Workspace states:
1. **Home shows on bare URL:** `#home` is visible, `.layout` is hidden. The coverage line reads "N of 728 classified … M untagged".
2. **Directories render:** Browse-by-System and Browse-by-Commodity tiles appear A–Z with counts; Browse-by-Market tiles appear Count-sorted with `Series (Region)` labels (e.g. `FMVSS (United States)`).
3. **Sort toggle:** clicking "Count" on the System panel reorders tiles by count; the active toggle highlights.
4. **Show all:** clicking "Show all (N more)" reveals the remaining tiles; "Show fewer" collapses.
5. **Tile → Workspace:** click a System tile (e.g. Crashworthiness) → `#home` hides, `.layout` shows, the System facet is checked, results are filtered, URL has `?systems=Crashworthiness`.
6. **Home link returns Home:** click the header title → Home shows again, filters cleared.
7. **Search from Home:** type in the search box on Home → switches to Workspace with results; clearing the box returns to Home.
8. **Light default:** with no `localStorage.theme`, `document.documentElement` has `data-theme="light"`. `Ctrl+K` focuses the search input.
9. **Deep link:** navigating directly to `http://localhost:8137/?commodities=Seats` lands in the Workspace (not Home) with Seats pre-filtered.

- [ ] **Step 3: Record results, then stop the server.**

If all pass, Phase 2 is complete.

---

## Self-review checklist (run before execution)
- **Spec §7 coverage:** hero + coverage line (Task 4), System/Commodity panels A–Z + Count toggle + Top-N/more (Tasks 4–5), Market panel Count default + `Series (Region)` (Task 4), tile→Workspace (Task 6), light default + Ctrl+K (Task 1). ✓
- **No data/build changes needed:** `region_series` and all counts come from Phase 1's `taxonomy.json`/`index.json`. ✓
- **Reuses existing machinery:** navigation goes through `applyUrlParams()`/`render()` so the Workspace behaves identically to a manually-typed URL. ✓
- **Coverage honesty:** untagged count shown; "browse all by market" escape hatch present; nothing hidden (Workspace still shows all via search/region). ✓

## Execution handoff
After Phase 2 lands, Phase 3 (Workspace: filter chips, group-by-market, side reading pane, tiered/folded
filters) gets its own plan against the same spec.
