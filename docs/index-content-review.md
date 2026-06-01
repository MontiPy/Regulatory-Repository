# index.html Content Review & Recommendations

_Review date: 2026-06-01 · Corpus: 728 regulations in `regulations/`_

## Summary

`index.html` faithfully renders every field the data model allows, but the
**data doesn't yet justify every UI element**. Several filters and badges are
driven by fields that are uniform (every record has the same value) or empty
(no record has any value). These add visual noise and imply filtering power
that doesn't exist. The recommendations below are ordered by impact-to-effort.

---

## 1. Remove the Status filter and the always-on "Active" badge — HIGH impact

**Finding:** All 728 records have `status: in-force`. The Status facet offers
four options (Active / Proposed / Withdrawn / Superseded) but only one has any
members, so the filter can never narrow results. Worse, the green **"Active"**
badge renders on *every single card* — 728 identical badges that convey nothing.

**Recommendation:**
- Suppress the status badge when `status === "in-force"`. Show a badge **only**
  for the exception states (proposed/withdrawn/superseded), which actually carry
  signal. (This makes the badge meaningful the day a non-active record appears.)
- Hide the Status filter section until ≥2 distinct statuses exist in the corpus
  (a one-line guard: only render a facet whose populated value-count is > 1).

This is the single largest noise reduction available.

## 2. Drop the per-card "Untagged" badge — HIGH impact

**Finding:** 630 of 728 cards (86%) show the **"Untagged"** badge. Badging the
*majority* is backwards — a badge should flag the exception, not the norm.

**Recommendation:**
- Remove the "Untagged" badge from the card face.
- Keep the **Tagging Status** filter — it is the legitimate way to surface the
  98 tagged records. (Optionally invert: show a subtle "Tagged" marker on those
  98 instead.)

## 3. Keep the Translation filter, but fix its backing data — MEDIUM impact

**Finding (corrected after reconciling with git):** Translation is an *active*
feature, not a dormant one — the recent commits translate 78 KMVSS articles and
add the `translation_status` field, and `backfill_translation.py` exists. In the
**committed** repository those KR articles carry `translation_status: translated`
with English bodies, so the facet has a real, populated "translated" group.

Two data-hygiene problems sit behind the filter, though:
- **463 records have no `translation_status` value at all.** They fall into a
  phantom "(unset)" group that the facet can't represent cleanly.
- **Working-tree anomaly:** the local checkout currently has **82 `kr-*.md`
  files modified back to Korean text with `translation_status: untranslated`**,
  contradicting the committed `translated` state. A build from this working tree
  would show those 78+ articles as untranslated Korean. Confirm this revert is
  intended before rebuilding `dist/index.html`.

**Recommendation:**
- **Keep** the Translation facet — it is a legitimate dimension.
- Backfill the 463 unset records to an explicit value (almost certainly
  `untranslated`) so the field is consistent and the facet has no "(unset)"
  ghost group. `backfill_translation.py` looks like the right tool.
- Verify the 82 modified KR files in the working tree are intentional; otherwise
  the translated content the user just committed will silently disappear from
  the next build.

## 4. Fix the search placeholder and dormant detail rows — MEDIUM impact

**Finding:** `un_equivalent`, `related`, and `aliases` are populated on **0**
records. The search box advertises "…UN equivalent, tags…" but a UN-equivalent
search can never match, and the "UN Equivalent"/"Related" rows in the expanded
card never render.

**Recommendation:**
- Update the search placeholder to drop "UN equivalent" until data exists
  (e.g. "Title, citation, tags, or body text…").
- Leave the conditional render code for UN Equivalent / Related in place (it's
  harmless and correctly hidden) — this is a data gap, not a UI bug.

## 5. Add a "full text available" toggle for stubs — MEDIUM impact (product call)

**Finding:** 195 records are `source_api: spreadsheet` (rendered with a
"Full text not available" banner), 126 are paywalled, and 55 have bodies under
200 characters. Roughly a quarter of results are catalog stubs with little or
no readable text, interleaved with full-text records.

**Recommendation (decide based on the repo's purpose):**
- If the repo is a **searchable text library**: add a "Full text only" toggle
  (default on) so stubs are hidden unless explicitly requested, and/or sort
  stubs below full-text records.
- If it is a **completeness catalog**: keep them all, but the stub banner
  already distinguishes them — no change needed.

This is the one item that depends on intent rather than data, so it's flagged
as a decision rather than a fix.

## 6. Hide zero-count facet options — LOW impact

**Finding:** Of the taxonomy, 21/23 systems and 25/31 commodities are actually
used; all 7 vehicle categories are used. The unused options render dimmed at
count 0. The existing `.empty` dimming handles this acceptably.

**Recommendation:** Optional — fully hide options whose corpus count is 0
(rather than dimming) to shorten the System/Commodity lists. Low priority.

## 7. Tiny-count regions — NO change

**Finding:** Several regions have 1–3 records (AR, IL, TR, TW = 1 each; MX, NZ,
ZA, EAEU = 2). This is normal long-tail coverage, and the region facet counts
already communicate it. No action.

---

## Suggested order of work

1. Status badge + Status filter guard (#1)
2. Remove Untagged badge (#2)
3. Confirm the 82-file KR working-tree revert, then backfill `translation_status` (#3)
4. Search placeholder cleanup (#4)
5. Decide stub visibility policy (#5)

Items 1, 2, 4 are small, localized template edits. #3 is data hygiene (plus a
working-tree check that should happen before the next build). #5 is a product
decision; #6 is optional polish.

> **Build scope note:** `regulations/` also contains `archive/` and `_test_kr/`
> subdirectories, but `build.py` globs only `regulations/*.md` (non-recursive),
> so neither produces cards. The 728 built records are correct — no duplicates.
> `_test_kr/` is stray test scaffolding worth removing from the repo for tidiness.
