# Regulatory Repository UI/UX Final Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the generated static Regulatory Repository UI by fixing reader readability, result scanning, mobile filter behavior, and keyboard accessibility while preserving the current restrained Honda-style industrial design.

**Architecture:** Keep the existing static app architecture: `scripts/build.py` generates data into `dist/data`, `templates/index.html.j2` defines the shell, and source assets in `assets/app.js` and `assets/styles.css` are copied into `dist/assets`. Do not introduce a framework or a separate runtime; make focused improvements in the current HTML/CSS/vanilla JS surface.

**Tech Stack:** Python 3.11 build pipeline, Jinja2 shell template, vanilla JavaScript, CSS, MiniSearch, pytest, local browser smoke testing against `dist/index.html`.

---

## Final Position After Reviewing the Counter Proposal

Adopt the counter-proposal's core technical correction: the reader body is starved primarily because `.expanded-cols` uses a viewport media query while living inside a narrower reader container. Fix that before considering a full-page reader.

My counter to the counter-proposal:

- Do not split the reader layout fix and trust-header work into separate phases. They touch the same reader DOM/CSS and should ship together so the reader has both readable text and clear source/status context.
- Do not leave `summary_text` cleanup as an indefinite parallel data track. The result-card work is incomplete unless display summaries stop showing inline `Regulated Area:` / `Applicability:` scaffolding.
- Do not prioritize pagination yet. Keep `Load more` for this iteration; add sort/order clarity and better snippets first.
- Do not create separate citation/search modes. Keep the unified search and make its scope clearer.

## Files To Touch

- Modify: `templates/index.html.j2`
  - Add `aria-controls` for filters.
  - Add reader header/trust containers.
  - Add a mobile filter close button for the drawer implementation.

- Modify: `assets/styles.css`
  - Replace viewport-governed reader interior split with a reader/container-width governed layout.
  - Add reader trust-header styles.
  - Add mobile filter drawer/sheet styles.
  - Add keyboard-friendly tooltip and focus styles.
  - Tune result-card metadata/snippet spacing.

- Modify: `assets/app.js`
  - Fill reader trust/status metadata.
  - Preserve focus origin when opening/closing reader.
  - Add Escape handling for reader and mobile filters.
  - Convert filter info tooltip triggers to keyboard/touch reachable controls.
  - Add body-match snippets for search results.
  - Improve facet hidden-count copy.

- Modify: `scripts/build.py`
  - Clean display summaries so generated `summary_text` does not embed metadata-label scaffolding as prose.

- Modify: `tests/test_build.py`
  - Add summary cleanup tests.
  - Add shell/static asset assertions for accessibility-critical hooks where practical.

- Generated but do not hand-edit: `dist/index.html`, `dist/assets/app.js`, `dist/assets/styles.css`, `dist/data/index.json`, `dist/data/search-text.json`
  - Regenerate these by running `python scripts/build.py`.

## Non-Goals

- No React, Vue, routing library, CSS framework, or table component library.
- No separate citation-search mode.
- No deferred mobile filter `Apply` button; filtering remains live.
- No full-page reader route in this iteration.
- No pagination redesign unless later testing proves `Load more` is insufficient.

---

### Task 1: Reader Layout And Trust Header

**Files:**
- Modify: `templates/index.html.j2`
- Modify: `assets/styles.css`
- Modify: `assets/app.js`
- Verify generated: `dist/index.html`, `dist/assets/styles.css`, `dist/assets/app.js`

- [ ] **Step 1: Add reader header structure to the template**

In `templates/index.html.j2`, keep the reader inside the existing `<aside id="reader">`, but replace the single title/close row with a title block that can receive trust metadata:

```html
<aside class="reader hidden" id="reader" aria-label="Regulation reader">
  <div class="reader-head">
    <div class="reader-title-block">
      <strong class="reader-title" id="reader-title"></strong>
      <div class="reader-trust" id="reader-trust" aria-label="Reader source details"></div>
    </div>
    <button type="button" class="reader-close" id="reader-close" aria-label="Close reader">×</button>
  </div>
  <div class="reader-body" id="reader-body"></div>
</aside>
```

- [ ] **Step 2: Replace the viewport reader split with container-governed CSS**

In `assets/styles.css`, replace the current `.expanded-cols` viewport media query with container-based behavior. Use a single column by default and only split when the reader content container is actually wide enough.

```css
.expanded {
  display: grid;
  gap: 16px;
  margin-top: 18px;
  border-top: 1px solid var(--line-1);
  padding-top: 18px;
  container-type: inline-size;
}

.expanded-cols {
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 1fr);
}

@container (min-width: 760px) {
  .expanded-cols {
    grid-template-columns: minmax(0, 1.8fr) minmax(240px, 0.8fr);
    align-items: start;
  }
}
```

Remove the old `@media (min-width: 1100px)` rule for `.expanded-cols`.

- [ ] **Step 3: Style the reader trust header**

Add compact trust chips below the title without turning the header into a dense card:

```css
.reader-title-block {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.reader-title {
  font-size: 14px;
  font-weight: 900;
  color: var(--fg-1);
  line-height: 1.35;
}

.reader-trust {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: var(--fg-3);
  font-size: 11px;
}

.reader-trust-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 20px;
  padding: 2px 7px;
  border: 1px solid var(--line-1);
  background: var(--surface);
  color: var(--fg-2);
  line-height: 1.25;
}

.reader-trust-chip.source a {
  color: inherit;
  text-decoration: underline;
}
```

- [ ] **Step 4: Populate trust metadata in `assets/app.js`**

Add helper functions near `readerBodyHtml(record)`:

```js
function sourceLinkHtml(record) {
  if (!record.source_url) return "";
  return `<a href="${escapeHtml(record.source_url)}" rel="noopener noreferrer">${escapeHtml(hostLabel(record.source_url))} ↗</a>`;
}

function readerTrustHtml(record) {
  const chips = [];
  if (record.status) chips.push(`<span class="reader-trust-chip">${escapeHtml(displayLabel(record.status))}</span>`);
  if (record.citation) chips.push(`<span class="reader-trust-chip">${escapeHtml(record.citation)}</span>`);
  if (record.source_url) chips.push(`<span class="reader-trust-chip source">Source: ${sourceLinkHtml(record)}</span>`);
  if (record.last_pulled) chips.push(`<span class="reader-trust-chip">Pulled ${escapeHtml(record.last_pulled.slice(0, 10))}</span>`);
  if ((record.un_equivalent_ai || []).length) chips.push(`<span class="reader-trust-chip">AI equivalent needs verification</span>`);
  return chips.join("");
}
```

Then update `openReader(id)` after setting `#reader-title`:

```js
document.querySelector("#reader-trust").innerHTML = readerTrustHtml(record);
```

Reuse `sourceLinkHtml(record)` inside `readerBodyHtml(record)` so the source link is not constructed twice.

- [ ] **Step 5: Verify reader layout manually**

Run:

```powershell
python scripts/build.py
```

Expected: `.build_report.txt` is updated and the command exits successfully.

Open:

```text
dist/index.html?q=braking
```

Expected:

- Opening `ADR 31/04 - Brake Systems for Passenger Cars` shows readable legal text.
- Metadata is below the body unless the reader content container is wide enough.
- Reader header shows compact status/citation/source/pulled information.
- No source/status data is duplicated awkwardly.

---

### Task 2: Result Card Snippets And Display Summary Cleanup

**Files:**
- Modify: `assets/app.js`
- Modify: `assets/styles.css`
- Modify: `scripts/build.py`
- Modify: `tests/test_build.py`
- Verify generated: `dist/data/index.json`, `dist/data/search-text.json`, `dist/assets/app.js`, `dist/assets/styles.css`

- [ ] **Step 1: Add failing summary cleanup tests**

In `tests/test_build.py`, add tests for a new helper such as `clean_summary_display_text` imported from `scripts.build`:

```python
from scripts.build import clean_summary_display_text


def test_clean_summary_display_text_removes_metadata_scaffold_after_useful_title():
    raw = (
        "Argentina model configuration and environmental configuration licenses "
        "Regulated Area: Market access / type approval / emissions "
        "Applicability: Applies to new vehicles for public-road circulation in Argentina"
    )
    assert clean_summary_display_text(raw) == (
        "Argentina model configuration and environmental configuration licenses"
    )


def test_clean_summary_display_text_keeps_short_plain_summary():
    assert clean_summary_display_text("Brake systems for passenger cars") == (
        "Brake systems for passenger cars"
    )
```

- [ ] **Step 2: Run the targeted failing test**

Run:

```powershell
pytest tests/test_build.py -k clean_summary_display_text -v
```

Expected: FAIL because `clean_summary_display_text` does not exist yet.

- [ ] **Step 3: Implement display-summary cleanup**

In `scripts/build.py`, add:

```python
SUMMARY_SCAFFOLD_RE = re.compile(
    r"\s+(?:Regulated Area|Applicability|Source|Notes):\s+",
    re.IGNORECASE,
)


def clean_summary_display_text(plain: str) -> str:
    text = unescape(re.sub(r"\s+", " ", plain or "")).strip()
    match = SUMMARY_SCAFFOLD_RE.search(text)
    if match and match.start() >= 40:
        return text[: match.start()].rstrip(" .;:-")
    return text
```

Then update `summarize(body_html)` so cleanup happens before truncation:

```python
def summarize(body_html: str) -> str:
    plain = bleach.clean(body_html, tags=[], strip=True)
    plain = clean_summary_display_text(plain)
    if len(plain) <= 250:
        return plain
    cutoff = plain.rfind(" ", 0, 250)
    if cutoff < 180:
        cutoff = 250
    return plain[:cutoff].rstrip() + "..."
```

- [ ] **Step 4: Rerun summary tests**

Run:

```powershell
pytest tests/test_build.py -k clean_summary_display_text -v
```

Expected: PASS.

- [ ] **Step 5: Add runtime body-match snippet support**

In `assets/app.js`, store search documents when `data/search-text.json` loads:

```js
let searchDocsById = new Map();
```

Inside `loadSearch()` after `docs` loads:

```js
searchDocsById = new Map(docs.map((doc) => [doc.id, doc.text || ""]));
```

Add helpers near `highlight` or `matchesText`:

```js
function baseSearchText(record) {
  return [
    record.title,
    record.citation,
    (record.aliases || []).join(" "),
    record.summary_text,
    (record.un_equivalent || []).join(" "),
    (record.tags || []).join(" "),
    (record.open_tags || []).join(" "),
  ].join(" ");
}

function bodyMatchSnippet(record, query) {
  const q = normalize(query).trim();
  if (!q || q.length < 3 || normalize(baseSearchText(record)).includes(q)) return "";
  const text = searchDocsById.get(record.id) || "";
  const lower = normalize(text);
  const idx = lower.indexOf(q);
  if (idx < 0) return "";
  const start = Math.max(0, idx - 90);
  const end = Math.min(text.length, idx + q.length + 140);
  const prefix = start > 0 ? "..." : "";
  const suffix = end < text.length ? "..." : "";
  return `${prefix}${text.slice(start, end).trim()}${suffix}`;
}

function cardSummaryHtml(record, query) {
  const snippet = bodyMatchSnippet(record, query);
  if (snippet) {
    return `<p class="summary summary-snippet">${highlight(snippet, query)}</p>`;
  }
  return `<p class="summary">${highlight(record.summary_text || "No summary available.", query)}</p>`;
}
```

Then change `cardTemplate(record)` to call:

```js
${cardSummaryHtml(record, q)}
```

- [ ] **Step 6: Add small visual distinction for body snippets**

In `assets/styles.css`, add:

```css
.summary-snippet {
  border-left: 2px solid var(--line-1);
  padding-left: 10px;
}
```

- [ ] **Step 7: Verify regenerated summaries and body-match behavior**

Run:

```powershell
python scripts/build.py
pytest tests/test_build.py -k "clean_summary_display_text or search_text" -v
```

Expected:

- Build succeeds.
- Targeted pytest selection passes.
- `dist/data/index.json` no longer displays workbook summaries with inline `Regulated Area:` / `Applicability:` scaffolding as the first card prose.
- A query that matches body-only text shows a body-context snippet; title/summary matches continue to show the normal summary with highlighting.

---

### Task 3: Mobile Filter Drawer With Live Updates

**Files:**
- Modify: `templates/index.html.j2`
- Modify: `assets/styles.css`
- Modify: `assets/app.js`

- [ ] **Step 1: Add filter toggle ownership**

In `templates/index.html.j2`, update the mobile filter button:

```html
<button type="button" class="filters-toggle" id="filters-toggle" aria-expanded="false" aria-controls="filters-panel">Filters</button>
```

Add `id="filters-panel"` to the filters aside:

```html
<aside class="filters" id="filters-panel" aria-label="Filters">
```

- [ ] **Step 2: Add a mobile-only close control**

Inside `.filters-inner`, before `#clear-filters`, add:

```html
<button type="button" class="filters-close" id="filters-close" aria-label="Close filters">×</button>
```

- [ ] **Step 3: Convert mobile filter CSS from inline push to overlay drawer**

In the `@media (max-width: 860px)` block in `assets/styles.css`, replace the current `.filters` mobile rules with:

```css
.filters {
  display: none;
  position: fixed;
  inset: 114px 0 0 0;
  z-index: 35;
  border-right: none;
  border-bottom: 1px solid var(--line-1);
  padding: 12px 0;
  overflow: auto;
  box-shadow: 0 12px 30px rgba(35,36,41,0.22);
}

.filters.is-open {
  display: block;
}

.filters-inner {
  position: static;
  max-height: none;
}

.filters-close {
  display: inline-flex;
}
```

Outside the media query, hide `.filters-close` by default:

```css
.filters-close {
  display: none;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin: 0 16px 10px auto;
  border: 1px solid var(--line-1);
  background: transparent;
  color: var(--fg-2);
  cursor: pointer;
  font-size: 20px;
}
```

Do not add an Apply button. Existing checkbox changes continue to call `render()` immediately.

- [ ] **Step 4: Add JS open/close helpers**

In `assets/app.js`, replace the inline filter toggle listener with helpers:

```js
const filtersToggle = document.querySelector("#filters-toggle");
const filtersClose = document.querySelector("#filters-close");

function setFiltersOpen(open) {
  filtersRail.classList.toggle("is-open", open);
  filtersToggle.setAttribute("aria-expanded", String(open));
}

filtersToggle.addEventListener("click", () => {
  setFiltersOpen(!filtersRail.classList.contains("is-open"));
});

filtersClose.addEventListener("click", () => {
  setFiltersOpen(false);
  filtersToggle.focus();
});
```

- [ ] **Step 5: Improve hidden-count copy**

In `updateFacetCollapse()`, replace:

```js
btn.textContent = expanded ? "Show fewer" : `Show all (${hiddenCount} hidden)`;
```

With:

```js
const label = displayLabel(key).toLowerCase();
btn.textContent = expanded ? "Show fewer" : `Show ${hiddenCount} more ${label}`;
```

Add a small map so the hidden-count copy uses natural plural labels:

```js
const FACET_MORE_LABELS = {
  region: "regions",
  systems: "systems",
  commodities: "commodities",
  vehicle_categories: "vehicle categories",
  status: "statuses",
  tagging_status: "tagging statuses",
  translation_status: "translation statuses",
};
```

Then use:

```js
const label = FACET_MORE_LABELS[key] || "options";
btn.textContent = expanded ? "Show fewer" : `Show ${hiddenCount} more ${label}`;
```

- [ ] **Step 6: Verify mobile drawer behavior**

Run:

```powershell
python scripts/build.py
```

Open `dist/index.html?q=airbag` at about 390 px wide.

Expected:

- Filters open as an overlay/drawer, not inline content that pushes the results awkwardly.
- Checkbox changes update results live.
- Clear all still resets filters.
- Close dismisses the drawer and returns focus to `Filters`.
- No Apply button exists.

---

### Task 4: Keyboard Accessibility And Tooltip Reachability

**Files:**
- Modify: `assets/app.js`
- Modify: `assets/styles.css`
- Modify: `templates/index.html.j2` if reader controls need extra ARIA hooks

- [ ] **Step 1: Track reader focus origin**

In `assets/app.js`, add:

```js
let readerOrigin = null;
```

In the cards click listener, before opening a reader:

```js
readerOrigin = btn;
```

Change `closeReader()` to restore focus when appropriate:

```js
function closeReader({ restoreFocus = true } = {}) {
  openReaderId = null;
  document.querySelector("#reader").classList.add("hidden");
  document.querySelector(".layout").classList.remove("reading");
  document.querySelector("#reader-trust").innerHTML = "";
  render();
  syncUrl();
  if (restoreFocus && readerOrigin && document.contains(readerOrigin)) {
    readerOrigin.focus();
  }
}
```

- [ ] **Step 2: Move focus into reader on open**

After reader DOM is updated in `openReader(id)`, focus the close button:

```js
document.querySelector("#reader-close").focus();
```

Keep this behavior for the first implementation pass. It gives keyboard users an immediate visible control for closing the reader.

- [ ] **Step 3: Add Escape behavior**

Extend the global keydown handler:

```js
if (event.key === "Escape") {
  if (openReaderId) {
    event.preventDefault();
    closeReader();
    return;
  }
  if (filtersRail.classList.contains("is-open")) {
    event.preventDefault();
    setFiltersOpen(false);
    filtersToggle.focus();
    return;
  }
}
```

- [ ] **Step 4: Convert filter info trigger to a button**

In `buildFilters()`, replace:

```js
const infoIcon = filter.tooltip ? `<span class="filter-info" data-tooltip="${escapeHtml(filter.tooltip)}">i</span>` : "";
```

With:

```js
const infoIcon = filter.tooltip
  ? `<button type="button" class="filter-info" data-tooltip="${escapeHtml(filter.tooltip)}" aria-label="${escapeHtml(filter.label)} help">i</button>`
  : "";
```

In `assets/styles.css`, reset button styling for `.filter-info`:

```css
.filter-info {
  appearance: none;
  padding: 0;
  background: transparent;
}

.filter-info:hover,
.filter-info:focus-visible {
  border-color: var(--honda-red);
  color: var(--honda-red);
}
```

- [ ] **Step 5: Add focus/touch tooltip behavior**

Update the tooltip event wiring in `assets/app.js` so it responds to `focusin`, `focusout`, and click/touch as well as mouseover.

Use helper functions:

```js
function showTip(el) {
  tip.textContent = el.dataset.tooltip;
  tip.style.display = "block";
  const r = el.getBoundingClientRect();
  const tw = tip.offsetWidth;
  const left = (r.right + 10 + tw > window.innerWidth) ? r.left - tw - 10 : r.right + 10;
  tip.style.left = left + "px";
  tip.style.top = Math.max(8, r.top - 2) + "px";
  tip.setAttribute("aria-hidden", "false");
}

function hideTip() {
  tip.style.display = "none";
  tip.setAttribute("aria-hidden", "true");
}
```

Wire:

```js
document.addEventListener("mouseover", (event) => {
  const el = event.target.closest("[data-tooltip]");
  if (el) showTip(el);
});
document.addEventListener("mouseout", (event) => {
  if (!event.relatedTarget || !event.relatedTarget.closest("[data-tooltip]")) hideTip();
});
document.addEventListener("focusin", (event) => {
  const el = event.target.closest("[data-tooltip]");
  if (el) showTip(el);
});
document.addEventListener("focusout", (event) => {
  if (!event.relatedTarget || !event.relatedTarget.closest("[data-tooltip]")) hideTip();
});
```

- [ ] **Step 6: Verify keyboard behavior**

Run:

```powershell
python scripts/build.py
```

Manual checks:

- Press `/` from results: search focuses.
- Open a result with keyboard, reader opens, focus moves into reader.
- Press Escape: reader closes and focus returns to the originating result button.
- At mobile width, open filters, press Escape: filters close and focus returns to `Filters`.
- Tab to filter info `i` buttons: tooltip appears and is readable.

---

### Task 5: Home Search Scope And Sort/Order Clarity

**Files:**
- Modify: `templates/index.html.j2`
- Modify: `assets/app.js`
- Modify: `assets/styles.css`

- [ ] **Step 1: Keep unified search, but make scope legible**

Do not add separate citation/full-text modes. Update only the placeholder/help language.

In `templates/index.html.j2`, keep the single search input but make the placeholder concrete:

```html
placeholder="Search title, citation, tags, UN equivalent, or body text..."
```

- [ ] **Step 2: Add example query text without adding a landing-page instruction block**

Add a compact, low-emphasis examples line under the home hero coverage line:

```html
<p class="search-examples" id="search-examples">Try FMVSS 208, braking, airbag, or UN R13.</p>
```

These examples currently return results in `dist/data/index.json` as of 2026-06-18.

- [ ] **Step 3: Promote browse-all-by-market affordance**

Change the coverage-line inline link into a button-like text control or secondary button that calls the existing market browse behavior. Keep it visually restrained and avoid a hero marketing treatment.

- [ ] **Step 4: Add visible result order label**

Near `#result-count`, add a small order label in JS or template:

```html
<p id="result-order" class="result-order">Sorted by corpus order</p>
```

Do not implement sorting in this iteration. Label the current order honestly:

```html
<p id="result-order" class="result-order">Sorted by repository order</p>
```

- [ ] **Step 5: Verify examples**

Run a local rendered check for:

```text
dist/index.html?q=FMVSS%20208
dist/index.html?q=braking
dist/index.html?q=airbag
dist/index.html?q=UN%20R13
```

Expected: each shows at least one result in the current corpus.

---

## Verification Plan

Run after each task:

```powershell
python scripts/build.py
```

Run targeted tests after build/data changes:

```powershell
pytest tests/test_build.py -v
```

Run broader tests if the environment is stable:

```powershell
pytest -v
```

If broad pytest hits OneDrive or Windows temp locking issues, record the failure and run targeted tests plus rendered checks.

Rendered smoke scenarios:

- `dist/index.html?view=home`
- `dist/index.html?q=airbag`
- `dist/index.html?q=braking`
- Open the first braking result reader.
- Toggle dark mode.
- Mobile width around 390 px: open/close filters and change a checkbox.
- Keyboard: `/`, result open, Escape close, tooltip focus.

Pass criteria:

- Legal text is not trapped in a narrow column beside metadata at normal desktop widths.
- Reader header exposes status/citation/source/pulled trust context.
- Result cards do not use metadata scaffolding as summary prose.
- Body-only matches show contextual snippets; title/summary matches keep normal highlights.
- Mobile filters are an overlay/drawer with live updates, Clear, and Close.
- Escape and focus restoration work for reader and mobile filters.
- Filter info triggers are keyboard reachable.
- No relevant console/runtime errors.

## Execution Notes

- Make changes in source files under `assets/`, `templates/`, and `scripts/`; never hand-edit `dist/`.
- Regenerate `dist/` with `python scripts/build.py` after each source change.
- Keep commits task-sized if committing later.
- Preserve the current visual language: square corners, restrained red accents, dense but readable cards, and no landing-page redesign.
