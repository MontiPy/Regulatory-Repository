# Korean KMVSS Translation — Design Spec

**Date:** 2026-05-23  
**Status:** Approved

---

## Problem

79 Korean regulation files (`kr-kmvss-art*.md`) are marked `translation_status: untranslated`
and contain unusable content. The current connector scraped the law.go.kr page without JavaScript,
producing navigation chrome (social share buttons, file download dialogs, menus) instead of
regulatory text. The open.law.go.kr API key registration is blocked for non-Korean users
(requires Korean mobile carrier or national ID verification).

---

## Solution Overview

Three-phase approach:

1. **Fix the connector** — replace the broken HTML scraper with a fetch of the `lsInfoR.do`
   endpoint, which returns the full law body HTML in a single unauthenticated request.
2. **Re-pull** — regenerate all 79 KR files with clean Korean regulatory text.
3. **Archive + translate** — copy originals to an archive directory, then replace each file body
   with an English translation produced in-session by Claude Code.

---

## Phase 1 — Connector Fix

### Data source

The `lsInfoR.do` endpoint returns the complete KMVSS body in one request:

```
GET https://law.go.kr/LSW/lsInfoR.do
  ?lsiSeq=270023
  &efYd=20260320
  &efYn=Y
  &chrClsCd=010202
  &nwJoYnInfo=Y
  &ancYnChk=0
  &netPrivateYn=N
```

No authentication required. Response is a self-contained HTML fragment with all articles inline.

### Article extraction

Each article appears as a `<p class="pty1_p4">` element containing:
- A checkbox input whose `value` attribute encodes the article number
  (e.g., `value="10:0:001000:95777845"` → article 10)
- The article heading in a `<label>` element (e.g., `제10조(접지부분 및 접지압력)`)
- The article body text inline and in subsequent sibling elements

**Strategy:** fetch once, then for each manifest entry, locate the corresponding article block
and convert it to markdown. Sub-articles (e.g., article `12-2`) use the hyphen notation already
in the manifest.

### Connector changes (`connectors/law_go_kr.py`)

- Add `_fetch_full_law(session, law_id) -> str` — fetches `lsInfoR.do`, returns full HTML
- Add `_parse_article(html, article) -> tuple[str, str]` — extracts title + body for one article
- Replace `_fetch_public_html` with a call to the above two functions
- The `_fetch_with_api` path (API key mode) is unchanged
- Add `translation_status: untranslated` to every pulled record's frontmatter (connector sets it)

---

## Phase 2 — Re-pull

```
python scripts/pull.py --region KR
```

Overwrites all 79 existing `kr-*.md` files with clean Korean content. The manifest and slugs
are unchanged, so no downstream references break.

---

## Phase 3 — Archive and Translate

### Archive

Before translating, copy each `kr-*.md` file to:
```
regulations/archive/kr-original/<filename>.md
```

The `archive/` subdirectory is invisible to `scripts/build.py`, which globs only
`regulations/*.md` (non-recursive).

### Translation

Claude Code translates each file in-session:
- Read the Korean body
- Produce a full English translation preserving regulatory structure (article numbers, numbered
  lists, tables, cross-references)
- Write the English back to the original file path
- Update frontmatter: `translation_status: translated`

Files are processed in batches of several per turn to keep the session efficient. The Korean
original is always recoverable from `regulations/archive/kr-original/`.

### Translation notes

- Article headings (제N조): rendered as `## Article N — <English title>`
- Numbered lists (1., 2., 3.) and lettered sub-items preserved
- Cross-references to other articles (제N조) translated as "Article N"
- Measurement units, vehicle category names, and technical terms kept in standard English
  equivalents (e.g., "축하중" → "axle load", "최소회전반경" → "minimum turning radius")
- Amendment annotations (`<개정 YYYY. M. D.>`) rendered as `[Amended YYYY-MM-DD]`

---

## File Layout

```
regulations/
  kr-kmvss-art10.md          ← English body, translation_status: translated
  kr-kmvss-art12-2.md
  ...
  archive/
    kr-original/
      kr-kmvss-art10.md      ← Original Korean body (not built, not indexed)
      kr-kmvss-art12-2.md
      ...
```

---

## Out of Scope

- Re-translating JP (Japanese) files — same problem exists but is a separate task
- Adding the archive directory to the build pipeline
- Automated re-translation on re-pull (translation is a one-time in-session step; future
  re-pulls will overwrite with Korean again and require a new translation pass)
