# Regulatory Repository — HTML Tool UX Redesign

**Date:** 2026-06-04
**Status:** Design approved (brainstorming) → ready for implementation planning
**Scope:** The end-user experience of the generated web tool (today `dist/index.html`). The
pull → tag → build pipeline and connectors are out of scope except where the build step must
change to emit the new front-end bundle.

---

## 1. Context & current-state assessment

The repository pulls vehicle-regulation text from official government APIs, classifies records
against a controlled taxonomy, and builds a browsable web tool. The current tool is a single
self-contained `dist/index.html` (~16 MB) with strong fundamentals:

**What works (preserve):**
- Left-rail faceted search with live counts; OR-within-facet / AND-across-facet logic.
- Shareable URL state, dark mode, mobile filter drawer, keyboard shortcut (`/`), tooltips.

**Friction (research-grounded — see §3):**
- **No front door.** First-time users land on 50 cards + 7 collapsed facets with no wayfinding
  or "where do I start."
- **Applied filters are invisible.** Checking facet boxes produces no removable chips above
  results — the standard "what am I filtered to" pattern is missing.
- **Two competing filter systems.** A top "Show" availability bar and the left facet rail are
  separate mental models stacked together.
- **Flat facet hierarchy.** Region/System/Commodity (the actual job) sit in the same undistinguished
  list as Tagging Status and Translation (housekeeping metadata).

## 2. Users & primary journeys

Users are **vehicle engineers on Windows PCs** (internal). Journeys, in priority order:

- **A — "I own a part/system"** *(primary).* The Seats or Braking engineer wants every regulation
  touching their area, across all markets. The layout bends toward this.
- **C — "I have a specific reg in mind"** *(secondary).* Look it up, read it, ideally find
  equivalents.
- **D — "I'm exploring"** *(secondary).* Discover what coverage exists.
- **B — "I own a market/program"** *(deprioritized).* Region becomes a secondary cut, not the
  primary organizing axis.

## 3. Research findings (external)

- **Faceted search:** facets belong in the left rail; **6 well-chosen filters beat 20**; show top-N
  options + "show more"; **active filters must appear as removable chips** with "clear all"; counts
  per option aid orientation; desktop = persistent rail, mobile = drawer.
  ([Fact-Finder](https://www.fact-finder.com/blog/faceted-search/),
  [LogRocket](https://blog.logrocket.com/ux-design/advanced-ux-search-principles/))
- **Regulatory reference UIs (eCFR):** breadcrumbs, expand/collapse hierarchy, dedicated reader
  pages, strong wayfinding for hierarchical legal content.
  ([eCFR Reader Aids](https://www.ecfr.gov/reader-aids))
- **Information architecture / onboarding:** give users a visible sense of "where am I / what next";
  organize around user tasks, not internal structure; don't overwhelm on arrival.
  ([Parallel](https://www.parallelhq.com/blog/what-information-architecture))

## 4. Data realities that shaped the design

Measured on the current corpus (authoritative over stale README/TODO counts):

| Reality | Value | Design consequence |
|---|---|---|
| Total records | **728** (not the README's 98) | Must scale; docs are stale. |
| Tagged by commodity/system | **98 (13%)**; 630 untagged | A component-only front door would hide 87%. **Coverage-aware design is mandatory.** |
| Region coverage | **728 (100%)**, 21 markets | Region is the reliable full-coverage browse axis / fallback. |
| `summary_text` | Derived at build (`summarize(body_html)`) | Present for every record with a body. Safe to feature. |
| `un_equivalent` / `related` | **Empty across all 728** | "Equivalents & Related" renders **only when present**; not a hero feature. Tracked as a future data track. |
| Body sizes | 22 MB total; single regs up to **3.2 MB** | Embedding everything is untenable; bodies must lazy-load. |

## 5. Confirmed design decisions

| Decision | Value |
|---|---|
| Product structure | **Two views in one app: Home (front door) → Workspace (results)** |
| Hosting | **Internal/authenticated static host.** No backend. Full body text OK to serve. |
| File structure | Split: `index.html` shell + `assets/styles.css` + `assets/app.js` + `data/` |
| Data delivery | **Lightweight `index.json` upfront + lazy per-record `data/records/<id>.json` bodies** |
| Full-text search | **Body search included.** Prebuilt MiniSearch index, preloaded after Home first paint |
| Default theme | **Light** (toggle retained) |
| Platform | **Windows-first** — Segoe UI stack, **Ctrl+K** + `/` shortcuts, verify Edge/Chrome |
| Reading | **Side reading pane (Y)** — list left, reader right; URL-addressable `?id=`; full-screen on mobile; filter rail collapses to make room |
| Home: System/Commodity panels | **A–Z default**, Count toggle, expanded Top-N then "+ N more" |
| Home: Market panel | **Count default**, A–Z toggle; tiles `Series (Region)` with long region names |
| Region→series mapping | Stored in `taxonomy.yaml`; confirmed values in §9; EU + long-tail = TODO |

## 6. Architecture

Build (`build.py`) emits a **static bundle** deployable to any private static host:

```
dist/
├── index.html              minimal shell
├── assets/
│   ├── styles.css          (was inline)
│   └── app.js              (was inline; now view router + render)
└── data/
    ├── index.json          all records, light metadata (no bodies) — loaded once
    ├── taxonomy.json       vocabularies + region→series mapping (or inline in index.json)
    ├── search-index.json   prebuilt MiniSearch index (metadata + summary + body plaintext)
    └── records/
        └── <id>.json       full body_html per record — fetched on open, cached in memory
```

- **Client router** reads URL params (`?view=home` / `?system=…` / `?region=…` / `?q=…` / `?id=…`).
  Bare URL = Home. Any query/area/search param = Workspace. `?id=` opens the reading pane.
  Works on a plain static host (no server rewrites); all states deep-linkable & bookmarkable.
- **Counts** computed client-side from `index.json` over the bounded taxonomy (extends today's
  `CORPUS_COUNTS`), so directory tiles and coverage indicators are always accurate.
- **Preserve** the existing facet-match logic, URL-state sync, theme, and mobile-drawer code —
  this is a re-layering, not a rewrite.

### Search index strategy (de-risked)

- Builder: **MiniSearch** (small, serialisable). Index fields: title, citation, aliases, tags
  (commodities/systems/vehicle_categories), summary, **body plaintext** (HTML stripped).
- **Load strategy: preload after Home first paint** (idle), so search is warm before the user
  types — *not* on first keystroke.
- **Size budget:** target ≤ ~3 MB gzipped. Validated in Phase 1 by indexing the corpus and
  measuring. **Fallback:** if exceeded, index a body *excerpt* (first ~2 KB plaintext) instead of
  full bodies, and note full-body search as a later enhancement.

## 7. Home view

- **Header:** product title (links to Home) · prominent search · theme toggle.
- **Hero:** plain-language prompt ("Which regulations apply to your part, system, or market?") +
  large search; **coverage line**: "98 of 728 classified by part & system · browse all 728 by
  market · 630 untagged."
- **Browse by System** and **Browse by Commodity** panels (the bounded taxonomy): tiles with
  counts, **A–Z default** + Count toggle, expanded Top-N then "+ N more."
- **Browse by Market** panel: full-coverage fallback; tiles `Series (Region)`, **Count default** +
  A–Z toggle.
- Clicking any tile → Workspace pre-filtered. Searching → Workspace with the query.

## 8. Workspace view

- **Persistent header search** (Ctrl+K).
- **Filter chip bar** (above results): current area + every applied filter as **removable chips**,
  plus "Clear all." *(Fixes the invisible-filter gap.)*
- **Left rail:**
  - **Area** switcher — System/Commodity nav so users change area without returning Home.
  - **Refine** — secondary filters tiered by importance: **Region** (primary) and Vehicle Category /
    Status visible; **Tagging Status, Translation, and Availability under "More."** The old top
    "Show" availability bar is **folded in here** as one model. *(Fixes two-systems + flat hierarchy.)*
- **Results:** count + sort; **grouped by market** when an area is selected, group headers
  `United States · FMVSS (6)`. *(Serves journey A.)*
- **Reading pane (Y):** clicking a card opens the body on the right (lazy-fetched), list stays left;
  `?id=` in URL (deep-linkable, journey C); **Equivalents & Related shown only when populated**;
  source link, status, metadata. Narrow screens → full-screen reader; filter rail collapses.

## 9. Region → series mapping (`taxonomy.yaml`)

Confirmed from existing connectors/manifests:

| Region | Series | Long name | | Region | Series | Long name |
|---|---|---|---|---|---|---|
| US | FMVSS | United States | | JP | JVSR | Japan |
| CA | CMVSS | Canada | | BR | CONTRAN | Brazil |
| KR | KMVSS | South Korea | | CN | GB | China |
| AU | ADR | Australia | | GCC | GSO | Gulf Cooperation Council |
| ECE | UN R | UNECE | | IN | AIS | India |

**Open (tracked in TODO.md):** EU label (EUR-Lex = mixed Regulations + Directives; pick `EU`/`EC`);
long-tail labels for OTHER, ASEAN, ZA, NZ, MX, EAEU, TW, TR, IL, AR.

## 10. Coverage-aware behaviors

- Home coverage line states the truth (§7).
- Clicking a sparse area shows a note: *"18 classified under Crashworthiness. 630 records aren't
  classified yet — search to include them."*
- Untagged records are always reachable: **full-text search** (spans body), **Browse by Market**
  (100%), and an **Availability: Untagged** refine.
- No empty-looking dead ends: sparse/empty states explain why and offer the escape hatch.

## 11. Performance, responsive, accessibility

- **Performance:** `index.json` once → instant Home; search index preloaded post-paint; bodies
  lazy + cached. Gzip-friendly JSON. Fast first paint regardless of corpus size.
- **Responsive (Windows-desktop-first):** Home panels stack; Workspace rail → drawer; reading pane →
  full-screen; chip bar wraps.
- **Accessibility / keep:** URL-state sync, dark mode (default light), Ctrl+K + `/`, focus-visible,
  ARIA live region on counts.

## 12. Build & test

- `build.py` emits the bundle (shell + css + js + `data/`), derives summaries (unchanged), builds
  the search index, copies static assets, writes the region→series mapping.
- `tests/test_build.py` adds assertions: `index.json` schema + counts match corpus; per-record body
  files exist; search index builds and is within the size budget; untagged records present in index;
  region→series mapping resolves for every region in the corpus.
- Manual UX smoke-check via the Playwright MCP on the built bundle.

## 13. Implementation phasing

Independently shippable, in order:

1. **Phase 1 — Build/data rearchitecture.** Split inline HTML into shell + css + js; emit
   `index.json`, per-record bodies, `taxonomy.json`, search index; client router + lazy body fetch;
   preserve current results behavior. Validates the search-index size budget. *Ships behind the same
   UI; de-risks everything.*
2. **Phase 2 — Home view.** Directory front door, coverage line, sort toggles, market mapping.
3. **Phase 3 — Workspace.** Filter chips, tiered/folded filters, group-by-market, side reading pane,
   coverage-aware states.

## 14. Parallel / future tracks (own plans — see TODO.md)

- **Auto-tag the 630-record backlog** (`auto_tag.py`) — Path 1 of the agreed "Path 1 + Path 2"
  approach. Makes the component directory dense. Not a dependency (design works at 13% or 90%).
- **Populate `un_equivalent` / `related`** — unlocks the reading pane's equivalents panel (journey C).
- **Refresh stale docs** (README says 98 records / 6 regions; reality is 728 / 21).

## 15. Out of scope (YAGNI)

Auth/identity (handled by the host), multi-user editing, change-detection, in-app tagging,
server-side search/pagination.
