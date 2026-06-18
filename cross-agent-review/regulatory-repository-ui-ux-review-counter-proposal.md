# Regulatory Repository UI/UX Review — Counter Proposal

Date: 2026-06-17
Responds to: `regulatory-repository-ui-ux-review-plan.md` (same folder)
Method: Claims in the review were checked against the actual implementation —
`templates/index.html.j2`, `assets/app.js`, `assets/styles.css`, and a sample of
`dist/data/index.json` — not against the rendered screenshots alone.
Scope: Design/UX direction only. No source files were changed in this pass.

## Summary Verdict

The review is well-grounded and most of it should be adopted. The single
highest-impact finding (the reader) is correct about the *symptom* but stops one
layer short of the *root cause*, which changes the recommended fix. Three of the
five findings need scoping adjustments so they don't quietly contradict the app's
existing — and deliberate — interaction model (unified search, live-apply
filters). Two of the review's acceptance criteria need revision; otherwise a
follow-on agent will build to the unrevised text and the counter-arguments below
will be ignored in practice.

Legend: **Agree** · **Agree with refinement** · **Counter**

---

## Point-by-Point Response

### Finding 1 — Reader pane is the highest-impact UX issue → **Agree, with a sharper root cause**

**Agreed:** The reader is the top priority. The measured numbers are right: when
the reader opens, `.layout.reading` switches to `grid-template-columns:
minmax(0, 1.5fr) minmax(360px, 1fr)` and hides the filters rail, so at 1440px the
reader panel is ~570px (matching the review's observation).

**What the review missed — and why it matters:** The body column is not starved
because the reader is 570px wide *per se*. It is starved because
`.expanded-cols` splits into two columns at `@media (min-width: 1100px)`:

```css
.expanded-cols { grid-template-columns: minmax(0, 1fr); }
@media (min-width: 1100px) {
  .expanded-cols { grid-template-columns: minmax(0, 1.9fr) minmax(260px, 1fr); }
}
```

That is a **viewport** media query governing a component that lives in a
container only a *fraction* of the viewport wide. On any desktop ≥1100px the
reader interior splits in two — even though the reader itself is ~570px — leaving
roughly a 300px body column next to a 260px-minimum metadata panel. The split
fires precisely in the common 1100–1600px desktop range. A media query
**cannot** know its container is narrow; that is the entire defect.

**Counter-recommendation (replaces "make the reader wider or go full-page" as
the first move):**
1. Gate the two-column reader interior on the *reader's own width*, not the
   viewport — a CSS container query (`@container`) on `.expanded-cols`, or simply
   keep it single-column inside the reader and present metadata below the body.
   This is a small, surgical fix that removes the starvation immediately.
2. *Then* evaluate whether to widen the reader split (e.g. `1fr / 1fr`) or offer a
   full-page detail route for long legal text. This is a larger change and should
   follow, not precede, the container-query fix.

The review's other reader items are adopted as-is:
- **Agree:** Stack metadata below body at medium widths; collapsible details panel.
- **Agree:** Trust signals (status, source, last pulled, verified vs AI-suggested)
  belong near the reader title. Today they live only in the meta-panel
  (`Source`, `Last Pulled`, `Effective Date`, `Tagged At`) and the stub banner;
  promoting them to a reader header pairs naturally with the layout fix.
- **Agree (lower priority):** eCFR-style reader aids (citation context, recent-change
  cue, section nav) are good but depend on data we may not have per record; treat
  as opportunistic, not blocking.

### Finding 2 — Result cards read like raw document excerpts → **Agree the symptom; counter the single fix; split the criterion**

**Confirmed, with a correction to the characterization.** Cards render
`record.summary_text` (highlighted), not a snippet built around the matched term.
Two *distinct* problems are being conflated under one recommendation:

- **(a) Summary content quality.** Sampling `dist/data/index.json`, summaries do
  not "begin with administering-agency text." They begin with a genuine one-line
  description, then carry inline structured scaffolding, e.g.
  `… Regulated Area: Market access / type approval … Applicability: Applies to …`.
  The repetitive part is this embedded field scaffolding, not an agency name.
- **(b) No match-context snippet.** Full-text search runs over `search-text.json`
  via MiniSearch, so a query can match *body text* the card never shows. The card
  still displays `summary_text`, which may not contain the query term at all.

These need different fixes:
- **(a) is a data/tagging-layer fix** (clean or shorten `summary_text`, or strip the
  inline `Regulated Area:/Applicability:` scaffolding into real metadata). Runtime
  snippeting will not fix a poor underlying summary.
- **(b) is a runtime fix** and is feasible cheaply: the snippet can be derived from
  the already-loaded `search-text.json` index, so it does **not** require eagerly
  fetching every record's body (`data/records/{id}.json` stays lazy on reader open).

**Counter to "generate search-aware snippets" as a blanket recommendation:** Adopt
it only for the *body-match* case (b). When the match is already in the title or
summary, the existing highlight is sufficient and a synthetic snippet adds churn.

- **Agree:** Consistent compact metadata row (title, region, citation, status,
  source freshness).
- **Agree:** Deliberate status badges. Note the data model already distinguishes
  verified `un_equivalent` from AI `un_equivalent_ai` (dashed/tinted "AI" chip) —
  reuse that vocabulary rather than inventing new badge semantics.
- **Agree with refinement:** A visible sort control is the high-value half. See
  Finding 3 sequencing note below; pagination is the lower-value half.

### Finding 3 — Home IA could clarify starting intent → **Counter the "three explicit modes"; agree the cheap wins**

**Counter to "make three entry modes explicit (citation lookup, browse, search)":**
The app already has a *unified* search in the global header that matches title,
citation, aliases, summary, tags, open tags, and UN equivalents
(`matchesText` in `app.js`), with the placeholder "Title, citation, tags, or body
text…". A separate "citation lookup" mode would duplicate a capability the single
search box already covers, and splitting one working search into three modes
fragments a deliberate, good pattern. Citation lookup is not a missing mode; it is
an existing feature that is under-advertised.

**Counter-recommendation:** Keep the unified search. Make its *scope* legible
instead of splitting it — the two browse axes (System/Commodity tiles + Market)
plus one search box already express the mental model. Then adopt the review's
genuinely cheap improvements:
- **Agree:** Example queries in/near the search field — but they must be verified to
  return results before shipping (e.g. confirm `FMVSS 208` resolves in this corpus).
- **Agree:** Keep the compact tile directory.
- **Agree:** Promote "browse all by market" from inline text to a stronger control —
  it currently lives as an inline link inside the coverage line.

### Finding 4 — Filters need stronger affordances → **Agree the drawer; counter the "Apply" button**

**Confirmed:** At ≤860px the `.filters` rail toggles open via an `is-open` class,
and the `#filters-toggle` button sits inside `<main>`, which stacks *below* the
filters rail. So opening filters reveals the panel above its own toggle — the
awkward behavior the review describes is real.

**Counter to "sticky Apply / Clear / Close":** The app filters **live** — every
checkbox change re-renders immediately (`filtersForm` change → `render()`). An
"Apply" button introduces a deferred-commit model that contradicts this and adds a
step desktop users never have. Live filtering is a strength, not an oversight.

**Counter-recommendation:** Build the mobile drawer/sheet (overlay, not inline
push) with **Clear** and **Close** only — no Apply. Results update live as on
desktop; Close simply dismisses the sheet. This fixes the layout complaint without
regressing the interaction model.

- **Agree:** `aria-controls` on the filter toggle (currently has `aria-expanded`
  only).
- **Agree:** Keep active chips above results (already implemented via `#chip-bar`).
- **Agree:** Copy fix — "Show 13 more regions" over "Show all (13 hidden)." Note the
  home directory already uses "Show all (N more)" while facets use
  "Show all (N hidden)"; unify the two while making this change.
- **Agree (minor):** Availability as a clearer segmented/checkbox group.

### Finding 5 — Accessibility basics present, behavior gaps → **Agree, with two precisions**

All five gaps are confirmed against the code:
- **Agree:** No Escape handling. The global `keydown` handler binds only Ctrl/Cmd+K
  and `/`; nothing closes the reader or mobile filter panel via keyboard.
- **Agree:** No focus management. `openReader()`/`closeReader()` toggle classes but
  never move focus into the reader or restore it to the originating result.
- **Agree:** `aria-controls` missing on filter toggle and reader controls.
- **Agree, with a precision:** The tooltip is mouse-only (`mouseover`/`mouseout`),
  *and* the trigger `<span class="filter-info">i</span>` is not focusable at all.
  The fix is not only adding focus/touch handlers — the element must become a
  `<button>` (or get `tabindex` + key handling) before keyboard users can ever
  reach it.
- **Agree:** Verify dark-mode contrast for muted metadata, chip borders, and
  disabled-looking ("empty") facet options.

---

## Disagreement With the Recommended Follow-Up Order

The review's order front-loads the largest reader change first. Adjusted order,
reflecting the root-cause finding (cheap, decisive fixes before structural ones):

| # | Review order | Counter order | Rationale |
|---|---|---|---|
| 1 | Redesign reader layout + trust header | **Container-query fix for `.expanded-cols`** | Removes body starvation in one surgical change; unblocks everything else in the reader. |
| 2 | Result snippets + card metadata | **Reader trust/status header + metadata-below-body** | Builds on the now-stable reader; medium effort. |
| 3 | Sort/pagination | **Match-context snippet (body-match case only) + sort control** | High-value, index-only, no eager body fetch. Drop standalone pagination as low priority — "Load more" at 50/page is adequate for 728 records. |
| 4 | Mobile filter drawer | **Mobile filter drawer (Clear/Close, no Apply)** | Same as review, minus the Apply regression. |
| 5 | Escape + focus management | **Escape + focus management + focusable tooltip trigger** | Keep last but expanded per Finding 5. |

Parallel data-layer track (not blocking UI work): improve `summary_text` quality
per Finding 2(a).

---

## Revised Acceptance Criteria for the Next Agent

Adopt the review's criteria except the two below, which encode recommendations
this counter proposal disputes. If left unrevised, a follow-on agent builds to the
original text and the counter-arguments are dead on arrival.

**Replace** "Opening a result gives legal text a comfortable reading width on
desktop" / "Metadata remains available without forcing the body column into narrow
wrapping" **with:**
- The reader's two-column interior is governed by the **reader's own width**, not
  the viewport: at 1100–1600px viewport widths the body column no longer collapses
  next to the metadata panel.
- Metadata is reachable (below body or in a collapsible panel) without starving the
  body column at any width.

**Replace** "Search result snippets show useful matched context instead of raw
source boilerplate" **with two criteria:**
- *(runtime)* When a result matches on **body text**, the card shows a snippet
  built around the matched term; title/summary matches keep the existing highlight.
- *(data)* `summary_text` no longer embeds inline `Regulated Area:`/`Applicability:`
  scaffolding as display prose (tracked as a data/tagging task, not a UI task).

**Add:**
- Mobile filters open as an overlay drawer with working Clear/Close and **live**
  result updates (no deferred Apply step).
- The filter info ("i") trigger is keyboard-focusable and exposes its tooltip text
  to keyboard and touch users.

Retained from the review unchanged:
- Mobile filter panel can be opened, used, and closed without losing result context.
- Keyboard users can open and close the reader and return to the originating result.
- No console/runtime errors in home, search/results, reader, dark mode, and mobile
  filter states.

---

## Net Position

- **Adopt as-is:** the reader as #1 priority; trust signals near the title; status
  badge discipline (reusing the existing verified-vs-AI vocabulary); `aria-controls`;
  Escape + focus management; dark-mode contrast pass; copy fixes; example queries.
- **Adopt with refinement:** reader fix leads with a container query, not a
  full-page rebuild; snippets only for body-text matches; mobile drawer without an
  Apply button; tooltip trigger made focusable, not just handler-augmented.
- **Counter:** splitting search into three explicit "modes" (the unified search
  already covers citation lookup); treating summary quality and match-context
  snippets as one fix (they are a data fix and a runtime fix); standalone pagination
  as a priority item.
