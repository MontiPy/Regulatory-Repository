# Regulatory Repository UI/UX Review Plan

Date: 2026-06-17
Target: `dist/index.html`
Generator source of truth: `scripts/build.py`
Review type: Design and UX review only; no code changes made in this pass.

## Purpose

Review the generated static Regulatory Repository app with emphasis on the home directory, search/results/filter workspace, and regulation reader pane. The goal is to give a follow-on agent a concrete improvement plan that preserves the current restrained Honda-style industrial look while improving usability, scanning, and reader ergonomics.

## Surfaces Reviewed

- Home directory at `dist/index.html?view=home`
- Search/results workspace at `dist/index.html?q=airbag`
- Search interaction changing query from `airbag` to `braking`
- Reader pane opened from a braking result
- Dark mode reader state
- Mobile results and mobile filter panel at 390 px width

## Evidence Summary

- Build output reviewed from the generated app under `dist/index.html`.
- Build report present at `.build_report.txt`.
- Headless Edge render used after the in-app Browser backend was unavailable.
- Console/runtime issues during rendered checks: none observed.
- Temporary browser artifacts were removed after review.
- No source files were changed during the review pass.

Observed rendered counts:

- Home showed 728 regulations and 21 regions.
- `airbag` search showed 39 of 39 results.
- `braking` search showed 50 of 83 results.
- Reader split at 1440 px produced about 855 px for results and 570 px for reader.

## Reference Sites

Use these as comparison points, not templates to copy:

- USWDS: https://designsystem.digital.gov/
- GOV.UK search: https://www.gov.uk/search/all
- eCFR: https://www.ecfr.gov/
- IBM Carbon data table: https://carbondesignsystem.com/components/data-table/usage/
- Shopify Polaris index table: https://polaris-react.shopify.com/components/tables/index-table
- Mobbin: https://mobbin.com/
- Page Flows: https://pageflows.com/
- Landbook: https://land-book.com/
- Godly: https://godly.website/

## Findings

### 1. Reader pane is the highest-impact UX issue

At desktop width, the reader is about 570 px wide, then its content is split again between legal body text and a 260 px metadata panel. The body text column becomes too narrow, causing heavy wrapping in regulation titles and body content.

Recommended direction:

- Make the reader wider when open, or switch to a full-page/detail route for long legal text.
- Stack metadata below the body at medium widths instead of preserving a two-column reader interior.
- Consider a collapsible metadata/details panel.
- Move key trust signals near the reader title: status, source, last pulled, and verified vs AI-suggested equivalent state.
- Add reader aids inspired by eCFR: citation context, recent-change cue, source link, and clear section navigation where available.

### 2. Result cards are usable but read like raw document excerpts

The card hierarchy is clear, but many summaries begin with boilerplate such as administering agency text. This weakens scanning and makes search results feel less curated.

Recommended direction:

- Generate search-aware snippets around the matched term.
- Keep title, market/region, citation, status, and source freshness in a consistent compact metadata row.
- Use status badges deliberately: in force, repealed/no longer in force, paywall/no connector, AI inferred tags.
- Add a sort control or visible result ordering label.
- Add clearer pagination or list-progress controls instead of only `Load more`.

### 3. Home information architecture is clean but could clarify user starting intent

The home view is visually restrained and useful. Browse by System, Commodity, and Market are understandable, but the top-level user decision is still implicit.

Recommended direction:

- Make the three entry modes explicit: citation lookup, part/system browse, and full-text search.
- Add short example queries in or near the search field, such as `FMVSS 208`, `braking`, or `airbag`.
- Keep the current compact tile directory; it fits the repository task well.
- Consider exposing "browse all by market" as a stronger control rather than inline text.

### 4. Filters work, but the workflow needs stronger affordances

Active chips, visible counts, collapsed facets, and clear filters are good foundations. On mobile, the filter panel opens inline and pushes another `Filters` button below the panel, which feels awkward.

Recommended direction:

- Use a mobile drawer/sheet pattern with sticky `Apply`, `Clear`, and `Close` controls.
- Add `aria-controls` to the filter toggle.
- Keep active chips visible above results.
- Revisit hidden-count copy. "Show all (13 hidden)" is technically clear, but "Show 13 more regions" is more useful.
- Consider making availability a segmented control or checkbox group with clearer default copy.

### 5. Accessibility basics are present, with several behavior gaps

Positive basics observed:

- Search input has an accessible label.
- Checkboxes are inside labels.
- Result count uses `aria-live`.
- Focus-visible styles exist.
- Mobile filter toggle updates `aria-expanded`.
- Reader close button has an accessible label.

Recommended direction:

- Add Escape behavior for closing the reader and mobile filter panel.
- Move focus into the reader when it opens and restore focus to the originating result when it closes.
- Add `aria-controls` for filter toggle and reader controls.
- Ensure tooltip information is also available to keyboard and touch users.
- Test contrast in dark mode for muted metadata, chip borders, and disabled-looking text.

## Recommended Follow-Up Order

1. Redesign reader layout and reader trust/status header.
2. Improve generated result snippets and card metadata hierarchy.
3. Add sort/pagination or stronger list-progress affordances.
4. Rework mobile filters into a controlled drawer/sheet.
5. Add Escape and focus-management behavior for reader and filters.

## Acceptance Criteria For Next Agent

- Opening a result gives legal text a comfortable reading width on desktop.
- Metadata remains available without forcing the body column into narrow wrapping.
- Search result snippets show useful matched context instead of raw source boilerplate.
- Mobile filter panel can be opened, applied/cleared, and closed without losing result context.
- Keyboard users can open and close the reader and return to the originating result.
- No console/runtime errors in home, search/results, reader, dark mode, and mobile filter states.

