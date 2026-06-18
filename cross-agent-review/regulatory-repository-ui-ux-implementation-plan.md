# Regulatory Repository UI/UX — Final Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Date: 2026-06-18
Supersedes: `regulatory-repository-ui-ux-final-plan.md` (Codex's plan)
Relationship: This is **Codex's plan plus a small set of verified corrections (DELTAs)**. The task structure, sequencing, files-to-touch, and non-goals are Codex's and are adopted. Only the marked DELTAs change. Do not treat this as a fresh design — every change below was validated line-by-line against the current source.

---

## Assessment of Codex's Plan

**Verdict: correct and implementable, except for one blocking defect and four clarity/robustness fixes.** Verified against `scripts/build.py`, `assets/app.js`, `assets/styles.css`, `tests/test_build.py`, and `dist/data/index.json`:

| Codex claim / assumption | Status |
|---|---|
| Reader body starved by `@media (min-width:1100px)` on `.expanded-cols` (viewport query in a narrow container) | **Confirmed.** Lines 534–537 of `styles.css`. |
| Container-query fix is structurally sound (`.expanded-cols` is a child of `.expanded`) | **Confirmed.** `readerBodyHtml` nests `.expanded-cols` inside `.expanded`; `container-type: inline-size` on `.expanded` makes the query resolve. At 1440px the side reader's `.expanded` is ~540px, so it **stays single-column → body gets full width (the fix)**; it splits only on ultra-wide. |
| `summary_text` comes from `summarize(body_html)` so cleanup belongs there | **Confirmed.** Line 407 sets `"summary_text": summarize(body_html)`. The `Regulated Area:/Applicability:` scaffolding is in the stub body HTML, not a spreadsheet field. |
| `summarize(body_html)` signature, `re`/`unescape`/`bleach` imported | **Confirmed.** Lines 5, 10, 14, 277–285. |
| `tests/test_build.py` imports `from scripts.build import (...)` | **Confirmed.** Lines 10–11 (sys.path insert). New `clean_summary_display_text` import will work. |
| `last_pulled` exists for `.slice(0,10)` | **Confirmed.** Present on all 728 records, ISO format (`2026-06-01T18:54:42+00:00`). |
| Example queries return results | **Confirmed.** FMVSS 208→4, braking→43, airbag→28, UN R13→18. |
| Mobile `.filters` currently inline-pushes (`@media max-width:860px`) | **Confirmed.** Lines 758–760. |

**Codex's "counters to the counter-proposal" are accepted:** shipping reader layout + trust header together (same DOM), folding `summary_text` cleanup into the card work rather than an indefinite parallel track, keeping `Load more`, and keeping unified search are all sound. Items 3–4 actually align with the counter-proposal.

### Required changes from Codex's plan (DELTAs)

- **DELTA-1 (BLOCKER — would cause a regression):** Codex's `SUMMARY_SCAFFOLD_RE` matches `Regulated Area|Applicability|Source|Notes`. `summarize()` runs on **every** record, not just stubs, and `Source:` / `Notes:` appear routinely in real legal bodies (eCFR sections especially). With the `match.start() >= 40` guard, a genuine summary would be truncated mid-sentence. **Narrow the pattern to `Regulated Area|Applicability` only** and add a regression test proving a real body containing `Source:` survives uncut.
- **DELTA-2 (review-bait bug):** Codex changes `closeReader()` to `closeReader({ restoreFocus = true } = {})`, but `closeReader` is registered **directly** as the `#reader-close` click listener (`app.js:663`), so the browser passes a `PointerEvent` as the first argument. It works only by luck (the Event lacks a `restoreFocus` key). **Register the listener as `() => closeReader()`.**
- **DELTA-3 (silent no-op risk):** "Move focus into reader on open" must call `.focus()` **after** `#reader.classList.remove("hidden")`, or focusing a hidden element is a no-op.
- **DELTA-4 (consistency):** `route()` has an inline reader-close path (`app.js:496–500`) that bypasses `closeReader()`, so it won't clear the new `#reader-trust` or behave consistently. Route it through `closeReader({ restoreFocus: false })`.
- **DELTA-5 (honesty/polish):** The result-order label ("Sorted by repository order") is inaccurate when a System/Commodity facet is active, because `renderGrouped` re-orders by group size. Make the label grouping-aware (or hide it when grouped). Also add minimal CSS for `.search-examples`, which Codex references but never styles.

Everything not called out as a DELTA is adopted from Codex verbatim.

---

**Goal:** Improve the generated static Regulatory Repository UI — reader readability, result scanning, mobile filter behavior, keyboard accessibility — while preserving the restrained Honda-style industrial design.

**Architecture / Tech Stack / Non-Goals:** Unchanged from Codex's plan. Static app: `scripts/build.py` → `dist/data`; `templates/index.html.j2` shell; `assets/app.js` + `assets/styles.css` copied into `dist/assets`. No framework, no separate citation-search mode, no deferred mobile `Apply`, no full-page reader this iteration, no pagination redesign. Never hand-edit `dist/`; regenerate via `python scripts/build.py`.

## Files To Touch

- `templates/index.html.j2` — reader header/trust containers; `aria-controls`; mobile filter close button; search placeholder + examples line; result-order label.
- `assets/styles.css` — container-governed reader split; reader trust-header styles; mobile filter drawer; keyboard-friendly tooltip/focus; snippet spacing; **`.search-examples` (DELTA-5)**.
- `assets/app.js` — reader trust metadata; focus origin + Escape; focusable tooltip trigger; body-match snippets; hidden-count copy; **`closeReader` listener wrapper + inline-close routing (DELTA-2, -4)**; **grouping-aware order label (DELTA-5)**.
- `scripts/build.py` — `clean_summary_display_text` with **narrowed regex (DELTA-1)**, called inside `summarize()`.
- `tests/test_build.py` — Codex's two summary tests **plus the real-body regression test (DELTA-1)**.

---

### Task 1: Reader Layout And Trust Header

Adopt Codex Task 1 Steps 1, 3, 4 **as written**. Apply the DELTAs to Step 2 and the verify step.

- [ ] **Step 1 — reader header structure (Codex, unchanged):** replace the single title/close row in `templates/index.html.j2` with the `.reader-title-block` + `#reader-trust` structure from Codex Task 1 Step 1.

- [ ] **Step 2 — container-governed reader split (Codex, unchanged):** In `assets/styles.css`, replace the `.expanded` rule (lines 525–531) and the `.expanded-cols` viewport media query (lines 534–537) with Codex's container version: add `container-type: inline-size` to `.expanded`, keep `.expanded-cols` single-column by default, and split at `@container (min-width: 760px)`. Remove the old `@media (min-width: 1100px)` rule for `.expanded-cols`.
  - **Expectation note (not a change):** at a standard 1440px desktop the side reader stacks metadata **below** the body (single column) — that *is* the readability fix. The two-column interior appears only when the reader's own container is wide (ultra-wide monitors / full-screen reader at tablet widths). Do not "tune" 760px down expecting two columns at 1440px.

- [ ] **Step 3 — trust-header styles (Codex, unchanged).**

- [ ] **Step 4 — populate trust metadata (Codex, unchanged):** add `sourceLinkHtml(record)` and `readerTrustHtml(record)`; set `#reader-trust` innerHTML in `openReader` after the title; reuse `sourceLinkHtml` inside `readerBodyHtml`.

- [ ] **Step 5 — verify:** `python scripts/build.py`, open `dist/index.html?q=braking`, open `ADR 31/04 - Brake Systems for Passenger Cars`. Expect readable legal text, metadata **below** body at 1440px, compact status/citation/source/pulled chips in the header, no duplicated source/status.

---

### Task 2: Result Card Snippets And Display Summary Cleanup

Adopt Codex Task 2 Steps 5–7 (runtime body-match snippet + snippet CSS) **as written**. Apply **DELTA-1** to Steps 1–4.

- [ ] **Step 1 — failing summary tests (DELTA-1):** add Codex's two tests, **plus** a regression test that a real body is not over-truncated:

```python
def test_clean_summary_display_text_preserves_real_body_with_source_label():
    raw = (
        "This standard specifies requirements for occupant crash protection "
        "to reduce deaths and injuries. Source: 49 FR 12345. Compliance is "
        "required for vehicles manufactured on or after September 1, 2026."
    )
    # "Source:"/"Notes:" must NOT trigger truncation — only the workbook
    # scaffolding labels do.
    assert clean_summary_display_text(raw) == raw
```

Keep Codex's `..._removes_metadata_scaffold_after_useful_title` and `..._keeps_short_plain_summary` tests unchanged.

- [ ] **Step 2 — run failing test (Codex, unchanged):** `pytest tests/test_build.py -k clean_summary_display_text -v` → FAIL (function absent).

- [ ] **Step 3 — implement cleanup (DELTA-1: narrowed regex):**

```python
# Only the workbook stub scaffolding labels. Do NOT include generic
# "Source"/"Notes" — they occur in real legal bodies and summarize() runs
# on every record, not just stubs.
SUMMARY_SCAFFOLD_RE = re.compile(
    r"\s+(?:Regulated Area|Applicability):\s+",
    re.IGNORECASE,
)


def clean_summary_display_text(plain: str) -> str:
    text = unescape(re.sub(r"\s+", " ", plain or "")).strip()
    match = SUMMARY_SCAFFOLD_RE.search(text)
    if match and match.start() >= 40:
        return text[: match.start()].rstrip(" .;:-")
    return text
```

Then call it inside `summarize()` **before** truncation (Codex's edit, unchanged):

```python
def summarize(body_html: str) -> str:
    plain = bleach.clean(body_html, tags=[], strip=True)
    plain = unescape(re.sub(r"\s+", " ", plain)).strip()
    plain = clean_summary_display_text(plain)   # idempotent; safe after normalize
    if len(plain) <= 250:
        return plain
    cutoff = plain.rfind(" ", 0, 250)
    if cutoff < 180:
        cutoff = 250
    return plain[:cutoff].rstrip() + "..."
```

> Alternative if any false-positive risk remains unacceptable: gate cleanup to `source_api == "spreadsheet"` records by passing the record into `summarize()`. The narrowed regex is the lighter change and is sufficient given the regression test; prefer it unless the test surfaces a real over-match.

- [ ] **Step 4 — rerun (Codex, unchanged):** `pytest tests/test_build.py -k clean_summary_display_text -v` → PASS (all three, incl. the regression test).

- [ ] **Steps 5–7 — body-match snippet + CSS + verify (Codex, unchanged):** add `searchDocsById`, `baseSearchText`, `bodyMatchSnippet`, `cardSummaryHtml`; call `${cardSummaryHtml(record, q)}` in `cardTemplate`; add `.summary-snippet` CSS; verify build + targeted tests, and that body-only matches show a snippet while title/summary matches keep normal highlighting.

---

### Task 3: Mobile Filter Drawer With Live Updates

Adopt Codex Task 3 **in full, unchanged** (Steps 1–6: `aria-controls` + `id="filters-panel"`; mobile close button; overlay-drawer CSS replacing the inline push at lines 758–760; `setFiltersOpen` open/close helpers; hidden-count copy via `FACET_MORE_LABELS`; verify at 390px). No DELTAs. Keep live filtering — no `Apply` button.

---

### Task 4: Keyboard Accessibility And Tooltip Reachability

Adopt Codex Task 4 Steps 1, 3, 4, 5, 6. Apply **DELTA-2** and **DELTA-3** to Steps 1–2.

- [ ] **Step 1 — focus origin + `closeReader` (DELTA-2):** add `let readerOrigin = null;`; set `readerOrigin = btn;` in the cards click listener before opening. Change `closeReader` to accept options exactly as Codex shows **and also clear `#reader-trust`**:

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

  **DELTA-2 — fix the listener registration** so the click `PointerEvent` is not passed as the options object:

```js
// app.js:663 — was: addEventListener("click", closeReader)
document.querySelector("#reader-close").addEventListener("click", () => closeReader());
```

  **DELTA-4 — route the inline close path through it.** In `route()` (currently `app.js:496–500`), replace the inline `openReaderId = null; … remove("reading")` block with `closeReader({ restoreFocus: false });` so trust is cleared and behavior stays consistent.

- [ ] **Step 2 — focus into reader on open (DELTA-3):** in `openReader(id)`, call `document.querySelector("#reader-close").focus();` **after** `document.querySelector("#reader").classList.remove("hidden");` (focusing a hidden element is a silent no-op). Keep it after the `if (openReaderId !== id) return;` guard.

- [ ] **Step 3 — Escape behavior (Codex, unchanged):** extend the global keydown handler with the reader/filters Escape block.

- [ ] **Step 4 — filter info → `<button>` (Codex, unchanged):** convert the `.filter-info` span to a button with `aria-label`; add button-reset + focus-visible CSS.

- [ ] **Step 5 — focus/touch tooltip (Codex, unchanged):** add `showTip`/`hideTip` and wire `mouseover`/`mouseout`/`focusin`/`focusout`. (Touch is covered: tapping the button fires `focusin`.)

- [ ] **Step 6 — verify keyboard behavior (Codex, unchanged).**

---

### Task 5: Home Search Scope And Sort/Order Clarity

Adopt Codex Task 5 Steps 1–3, 5. Apply **DELTA-5** to Step 4 and add `.search-examples` CSS.

- [ ] **Step 1 — legible placeholder (Codex, unchanged):** `placeholder="Search title, citation, tags, UN equivalent, or body text..."`.

- [ ] **Step 2 — examples line (Codex, unchanged) + DELTA-5 CSS:** add `<p class="search-examples" id="search-examples">Try FMVSS 208, braking, airbag, or UN R13.</p>` under the coverage line. All four confirmed to return results in the current corpus (FMVSS 208→4, braking→43, airbag→28, UN R13→18). Add minimal CSS:

```css
.search-examples { font-size: 12px; color: var(--fg-3); margin: 8px 0 0; }
```

- [ ] **Step 3 — promote browse-all-by-market (Codex, unchanged):** restrained button-like control reusing existing market-browse behavior.

- [ ] **Step 4 — order label, grouping-aware (DELTA-5):** add `<p id="result-order" class="result-order"></p>` near `#result-count`. Do **not** implement sorting this iteration, but set the label honestly **in `render()`** based on whether grouping is active:

```js
const orderEl = document.querySelector("#result-order");
if (orderEl) {
  orderEl.textContent = areaSelected()
    ? "Grouped by market"          // renderGrouped() orders groups by size
    : "Sorted by repository order";
}
```

  This avoids claiming "repository order" while `renderGrouped` is actually ordering by group size.

- [ ] **Step 5 — verify examples (Codex, unchanged):** render-check `?q=FMVSS%20208`, `?q=braking`, `?q=airbag`, `?q=UN%20R13` — each ≥1 result.

---

## Verification Plan

Unchanged from Codex. After each task: `python scripts/build.py`. After build/data changes: `pytest tests/test_build.py -v` (then `pytest -v` if the environment is stable; if OneDrive/Windows temp locking interferes, record it and fall back to targeted tests + rendered checks).

Rendered smoke scenarios: `?view=home`, `?q=airbag`, `?q=braking`, open first braking result, toggle dark mode, mobile ~390px open/close filters + change a checkbox, keyboard `/` → open → Escape → tooltip focus.

**Pass criteria (Codex's, plus the DELTA assertions):**
- Legal text is not trapped in a narrow column beside metadata at normal desktop widths (stacks at 1440px).
- Reader header exposes status/citation/source/pulled trust context.
- Result cards do not use metadata scaffolding as summary prose **and real-body summaries are not truncated at `Source:`/`Notes:` (DELTA-1 regression test green).**
- Body-only matches show contextual snippets; title/summary matches keep normal highlights.
- Mobile filters are an overlay/drawer with live updates, Clear, and Close.
- Escape and focus restoration work for reader and mobile filters; **`#reader-close` click still closes the reader (DELTA-2).**
- Filter info triggers are keyboard reachable.
- Result-order label matches actual ordering in both flat and grouped modes (DELTA-5).
- No relevant console/runtime errors.

## Execution Notes

- Edit source under `assets/`, `templates/`, `scripts/`; never hand-edit `dist/`. Regenerate with `python scripts/build.py` after each source change.
- Keep commits task-sized. Preserve the visual language: square corners, restrained red accents, dense-but-readable cards, no landing-page redesign.
