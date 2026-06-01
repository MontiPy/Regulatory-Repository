# Korean KMVSS Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-pull 79 Korean KMVSS regulation files with clean regulatory text from the `lsInfoR.do` endpoint, archive the Korean originals, then translate all files to English in-session.

**Architecture:** Fix `law_go_kr.py` to fetch the full law body HTML via a single unauthenticated AJAX endpoint, parse individual articles from it with a per-law cache. After re-pull, copy originals to `regulations/archive/kr-original/`, then Claude Code translates each file body to English in-session and updates `translation_status: translated`.

**Tech Stack:** Python 3, `requests`, `beautifulsoup4` (already a transitive dep of `markdownify`), `markdownify`, `python-frontmatter`

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `connectors/law_go_kr.py` | Modify | Replace broken HTML scraper with `lsInfoR.do` fetcher + article parser |
| `regulations/archive/kr-original/` | Create dir | Korean originals before translation |
| `regulations/kr-*.md` (79 files) | Re-pulled then translated | Clean Korean → English |

---

## Task 1: Add article-parsing unit test

**Files:**
- Create: `tests/test_law_go_kr.py`

- [ ] **Step 1.1: Create the test file with a fixture and failing test**

```python
# tests/test_law_go_kr.py
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURE_HTML = """
<html><body>
  <p class="pty1_p4">
    <input name="joNoList" id="Y000900" type="checkbox"
           value="9:0:000900:111" />
    <span class="bl"><label for="Y000900"> 제9조(최소회전반경) </label></span>
    자동차의 최소회전반경은 12미터를 초과하여서는 아니된다.
  </p>
  <p class="pty1_p2">① 세부기준은 별표와 같다.</p>
  <p class="pty1_p4">
    <input name="joNoList" id="Y001000" type="checkbox"
           value="10:0:001000:222" />
    <span class="bl"><label for="Y001000"> 제10조(접지부분 및 접지압력) </label></span>
    접지부분 및 접지압력은 다음 각호의 기준에 적합하여야 한다.
  </p>
</body></html>
"""

FIXTURE_SUB_HTML = """
<html><body>
  <p class="pty1_p4">
    <input name="joNoList" id="Y001202" type="checkbox"
           value="12의2:0:001202:333" />
    <span class="bl"><label for="Y001202"> 제12조의2(타이어 압력 경보장치) </label></span>
    타이어 압력 경보장치의 기준은 다음과 같다.
  </p>
  <p class="pty1_p4">
    <input name="joNoList" id="Y001300" type="checkbox"
           value="13:0:001300:444" />
    <span class="bl"><label for="Y001300"> 제13조(조종장치) </label></span>
    다음 내용.
  </p>
</body></html>
"""


def test_parse_article_returns_title_and_body():
    from connectors.law_go_kr import _parse_article
    title, body = _parse_article(FIXTURE_HTML, "9")
    assert "제9조" in title
    assert "최소회전반경" in title
    assert "12미터" in body


def test_parse_article_stops_at_next_article():
    from connectors.law_go_kr import _parse_article
    _, body = _parse_article(FIXTURE_HTML, "9")
    assert "접지부분" not in body


def test_parse_article_includes_sub_paragraphs():
    from connectors.law_go_kr import _parse_article
    _, body = _parse_article(FIXTURE_HTML, "9")
    assert "세부기준" in body


def test_parse_sub_article():
    from connectors.law_go_kr import _parse_article
    title, body = _parse_article(FIXTURE_SUB_HTML, "12-2")
    assert "제12조의2" in title
    assert "타이어" in body
    assert "조종장치" not in body


def test_parse_article_missing_returns_fallback():
    from connectors.law_go_kr import _parse_article
    title, body = _parse_article(FIXTURE_HTML, "99")
    assert "99" in title
    assert "See source" in body
```

- [ ] **Step 1.2: Run tests — expect ImportError or AttributeError (functions don't exist yet)**

```
python -m pytest tests/test_law_go_kr.py -v
```

Expected: FAIL — `ImportError` or `cannot import name '_parse_article'`

---

## Task 2: Implement connector helper functions

**Files:**
- Modify: `connectors/law_go_kr.py`

- [ ] **Step 2.1: Add imports and constants at the top of `law_go_kr.py`**

Replace the existing imports block (lines 1–19) with:

```python
"""law.go.kr connector — pulls Korean motor vehicle safety standards (KMVSS).

Fetches the full law body from the lsInfoR.do AJAX endpoint (no auth required),
then parses individual articles by article number.

API key mode (KR_LAW_API_KEY env var) uses the open.law.go.kr JSON API instead.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, markdownify, write_md

API_BASE = "https://open.law.go.kr/LSO/openApi/lawService.do"
PUBLIC_BASE = "https://law.go.kr"
BODY_URL = f"{PUBLIC_BASE}/LSW/lsInfoR.do"

# Per-session cache: law_id → full HTML body from lsInfoR.do
_law_html_cache: dict[str, str] = {}
```

- [ ] **Step 2.2: Add `_article_label_pattern` function**

Insert after the constants block:

```python
def _article_label_pattern(article: str) -> re.Pattern[str]:
    """Return a compiled regex matching a Korean article label.

    '10'  → matches '제10조'
    '12-2' → matches '제12조의2'
    """
    if "-" in article:
        base, sub = article.split("-", 1)
        pat = rf"제\s*{re.escape(base)}\s*조의\s*{re.escape(sub)}"
    else:
        pat = rf"제\s*{re.escape(article)}\s*조\b"
    return re.compile(pat)
```

- [ ] **Step 2.3: Add `_parse_article` function**

```python
def _parse_article(full_html: str, article: str) -> tuple[str, str]:
    """Extract Korean title and markdown body for one article.

    Uses the lsInfoR.do full-law HTML. Article blocks are <p class='pty1_p4'>
    elements; content continues in following siblings until the next such block.
    """
    from bs4 import BeautifulSoup  # transitive dep of markdownify

    soup = BeautifulSoup(full_html, "html.parser")
    pattern = _article_label_pattern(article)

    label = None
    for lbl in soup.find_all("label"):
        if pattern.search(lbl.get_text()):
            label = lbl
            break

    if label is None:
        return f"KMVSS Article {article}", f"# KMVSS Article {article}\n\nSee source for full text."

    title_text = label.get_text(strip=True)  # e.g. "제10조(접지부분 및 접지압력)"

    container = label.find_parent("p")
    if container is None:
        return title_text, f"# {title_text}\n\nSee source for full text."

    # Collect this paragraph + following siblings until the next pty1_p4
    fragments: list[str] = [str(container)]
    for sib in container.next_siblings:
        if hasattr(sib, "get") and "pty1_p4" in (sib.get("class") or []):
            break
        fragments.append(str(sib))

    body_md = markdownify("".join(fragments))
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()
    return title_text, body_md or f"# {title_text}\n\nSee source for full text."
```

- [ ] **Step 2.4: Add `_discover_params` and `_fetch_full_law` functions**

```python
def _discover_params(session: RateLimitedSession, law_id: str) -> dict[str, str]:
    """Fetch the static lsInfoP.do page to discover efYd and chrClsCd."""
    url = f"{PUBLIC_BASE}/LSW/lsInfoP.do?lsiSeq={law_id}"
    resp = session.get(url)
    html = resp.text
    params: dict[str, str] = {
        "lsiSeq": law_id,
        "efYn": "Y",
        "nwJoYnInfo": "Y",
        "ancYnChk": "0",
        "netPrivateYn": "N",
    }
    m = re.search(r"efYd['\"]?\s*[=:,]\s*['\"]?(\d{8})", html)
    if m:
        params["efYd"] = m.group(1)
    m = re.search(r"chrClsCd['\"]?\s*[=:,]\s*['\"]?(\d+)", html)
    if m:
        params["chrClsCd"] = m.group(1)
    return params


def _fetch_full_law(session: RateLimitedSession, law_id: str) -> str:
    """Fetch lsInfoR.do once per law_id and cache the result."""
    if law_id in _law_html_cache:
        return _law_html_cache[law_id]
    params = _discover_params(session, law_id)
    resp = session.get(BODY_URL, params=params)
    html = resp.text
    # Verify we got actual article content, not an error page
    if 'class="pty1_p4"' not in html and "pty1_p4" not in html:
        raise RuntimeError(
            f"lsInfoR.do response for lsiSeq={law_id} contains no article blocks. "
            f"Params used: {params}. First 500 chars: {html[:500]}"
        )
    _law_html_cache[law_id] = html
    return html
```

- [ ] **Step 2.5: Run unit tests — expect PASS**

```
python -m pytest tests/test_law_go_kr.py -v
```

Expected: 5 tests pass.

- [ ] **Step 2.6: Commit**

```
git add connectors/law_go_kr.py tests/test_law_go_kr.py
git commit -m "feat(kr): add lsInfoR.do fetcher and article parser"
```

---

## Task 3: Update `pull()` to use the new fetcher

**Files:**
- Modify: `connectors/law_go_kr.py`

- [ ] **Step 3.1: Replace `_fetch_public_html` body with a call to the new functions**

Remove the entire `_fetch_public_html` function and replace it with this one-liner wrapper (keep the signature so the call site is minimal):

```python
def _fetch_public_html(session: RateLimitedSession, law_id: str, article: str) -> tuple[str, str]:
    full_html = _fetch_full_law(session, law_id)
    return _parse_article(full_html, article)
```

- [ ] **Step 3.2: Add `translation_status` to the record dict in `pull()`**

In the `record` dict inside `pull()` (the block that builds the record for `write_md`), add one field:

```python
record: dict[str, Any] = {
    "id": slug,
    "title": title,
    "region": "KR",
    "citation": citation,
    "status": "in-force",
    "source_url": src_url,
    "source_api": "law_go_kr",
    "tagging_status": "untagged",
    "translation_status": "untranslated",   # ← add this line
}
```

- [ ] **Step 3.3: Smoke-test by pulling a single article**

Temporarily, run:
```
python -c "
from pathlib import Path
from connectors.law_go_kr import pull
pulled = pull(Path('manifests/kr.yaml'), Path('regulations/_test_kr'))
print(f'Pulled {len(pulled)} files')
for p in pulled[:3]:
    print(p.name)
    print(open(p).read()[:300])
    print('---')
"
```

Expected: 79 files written to `regulations/_test_kr/`. Open one of them — the body should contain Korean regulatory text (not navigation menus or `javascript:;` links). Verify Article 9 mentions `12미터`, Article 10 mentions `접지부분`.

- [ ] **Step 3.4: Delete the test output directory**

```
python -c "import shutil; shutil.rmtree('regulations/_test_kr', ignore_errors=True)"
```

- [ ] **Step 3.5: Commit**

```
git add connectors/law_go_kr.py
git commit -m "feat(kr): pull clean article text via lsInfoR.do"
```

---

## Task 4: Re-pull all KR files

**Files:**
- Modify: `regulations/kr-*.md` (79 files, overwritten)

- [ ] **Step 4.1: Re-pull**

```
python scripts/pull.py --region KR
```

Expected output: 79 lines of `OK -> kr-kmvss-artN.md`. No failures.

- [ ] **Step 4.2: Spot-check two files**

Open `regulations/kr-kmvss-art9.md` — body must contain Korean text about turning radius, NOT `javascript:;` links or KakaoTalk share buttons.

Open `regulations/kr-kmvss-art102-2.md` — body must contain Korean regulatory content.

- [ ] **Step 4.3: Commit**

```
git add regulations/kr-*.md
git commit -m "chore(kr): re-pull 79 KR files with clean lsInfoR.do content"
```

---

## Task 5: Archive Korean originals

**Files:**
- Create: `regulations/archive/kr-original/` (directory + 79 files)

- [ ] **Step 5.1: Create the archive directory and copy files**

```python
# run this inline in Python or as a one-liner
import shutil
from pathlib import Path

src = Path("regulations")
dst = Path("regulations/archive/kr-original")
dst.mkdir(parents=True, exist_ok=True)

copied = 0
for f in sorted(src.glob("kr-*.md")):
    shutil.copy2(f, dst / f.name)
    copied += 1
print(f"Archived {copied} files to {dst}")
```

Run:
```
python -c "
import shutil
from pathlib import Path
src = Path('regulations')
dst = Path('regulations/archive/kr-original')
dst.mkdir(parents=True, exist_ok=True)
copied = [shutil.copy2(f, dst / f.name) for f in sorted(src.glob('kr-*.md'))]
print(f'Archived {len(copied)} files')
"
```

Expected: `Archived 79 files`

- [ ] **Step 5.2: Verify build.py ignores archive**

```
python scripts/build.py
```

Expected: dist/index.html rebuilds. The archive files must NOT appear in the output — confirm by checking that `regulations/archive/kr-original/kr-kmvss-art10.md` is NOT listed in REGS in `dist/index.html`.

```
python -c "
import json, re
html = open('dist/index.html').read()
m = re.search(r'const REGS = (\[.*?\]);', html, re.DOTALL)
regs = json.loads(m.group(1))
kr = [r for r in regs if r['region'] == 'KR']
print(f'{len(kr)} KR regs in dist — expected 79')
"
```

Expected: `79 KR regs in dist`

- [ ] **Step 5.3: Add archive directory gitignore note and commit**

Create `regulations/archive/.gitkeep`:
```
type nul > regulations\archive\.gitkeep
```

Then commit:
```
git add regulations/archive/
git commit -m "chore(kr): archive 79 Korean originals before translation"
```

---

## Task 6: Translate KR files in-session (Claude Code)

> **This task is performed by Claude Code directly in the conversation — no script needed.**
> Process files in batches of ~10 per turn for efficiency.

**Translation conventions:**
- Article heading `제N조(한국어 제목)` → `## Article N — <English title>`
- Sub-article `제N조의M(...)` → `## Article N-M — <English title>`
- Numbered/lettered lists: preserve structure, translate text
- Cross-references `제N조` → `Article N`
- Amendment annotations `<개정 YYYY. M. D.>` → `[Amended YYYY-MM-DD]`
- Technical terms: use standard automotive English (e.g., 축하중→axle load, 최소회전반경→minimum turning radius, 접지압력→ground pressure, 타이어→tire)
- Measurement values and numbers: keep as-is (Korean numerals → Arabic where applicable)
- `translation_status` frontmatter: update from `untranslated` → `translated`

**Files:**
- Modify: all `regulations/kr-*.md` (79 files)

- [ ] **Step 6.1: Translate batch 1 — articles art3 through art15**

Ask Claude Code in this session:
> "Translate the Korean body of each file in regulations/ matching kr-kmvss-art[3-9].md and kr-kmvss-art1[0-5].md. For each: read the file, replace the Korean body with an English translation, set translation_status: translated."

- [ ] **Step 6.2: Translate batch 2 — articles art15-2 through art30**

Continue in same session with the next batch.

- [ ] **Step 6.3: Translate batch 3 — articles art31 through art56**

- [ ] **Step 6.4: Translate batch 4 — articles art57 through art80**

- [ ] **Step 6.5: Translate batch 5 — articles art81 through art107 (end)**

- [ ] **Step 6.6: Verify all 79 files have translation_status: translated**

```
python -c "
import frontmatter
from pathlib import Path
files = sorted(Path('regulations').glob('kr-*.md'))
untranslated = [f.name for f in files if frontmatter.load(f).metadata.get('translation_status') != 'translated']
print(f'{len(files)} total, {len(untranslated)} still untranslated')
if untranslated:
    print('Missing:', untranslated[:10])
"
```

Expected: `79 total, 0 still untranslated`

- [ ] **Step 6.7: Commit translated files**

```
git add regulations/kr-*.md
git commit -m "feat(kr): translate all 79 KMVSS articles to English"
```

---

## Task 7: Rebuild dist and update TODO

**Files:**
- Modify: `dist/index.html`
- Modify: `TODO.md`

- [ ] **Step 7.1: Rebuild**

```
python scripts/build.py
```

- [ ] **Step 7.2: Verify KR entries appear in English in dist**

```
python -c "
import json, re
html = open('dist/index.html').read()
m = re.search(r'const REGS = (\[.*?\]);', html, re.DOTALL)
regs = json.loads(m.group(1))
kr = [r for r in regs if r['region'] == 'KR']
print(f'{len(kr)} KR regs')
sample = kr[0]
print('title:', sample['title'])
print('translation_status:', sample.get('translation_status'))
"
```

Expected: 79 KR regs, titles in English (e.g. "Article 9 — Minimum Turning Radius"), `translation_status: translated`.

- [ ] **Step 7.3: Update TODO.md**

Mark the Korean translation task as done:
```
- [x] ~~Translate Korean-language content (KMVSS) to English~~ — **DONE** — 79 articles translated in-session; Korean originals archived to `regulations/archive/kr-original/`
```

- [ ] **Step 7.4: Final commit**

```
git add dist/index.html TODO.md
git commit -m "feat(kr): rebuild dist with translated KR regulations; close TODO"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Fix connector to use `lsInfoR.do` — Task 2–3
- ✅ Re-pull 79 files with clean Korean — Task 4
- ✅ Archive Korean originals to `regulations/archive/kr-original/` — Task 5
- ✅ Archive invisible to build pipeline — Task 5 Step 5.2
- ✅ Translate in-session with Claude Code — Task 6
- ✅ `translation_status: translated` set on all files — Task 6 Step 6.6
- ✅ `translation_status: untranslated` set on re-pull — Task 3 Step 3.2
- ✅ Rebuild dist — Task 7
- ✅ TODO updated — Task 7 Step 7.3

**Placeholder scan:** No TBDs. All code blocks complete.

**Type consistency:** `_parse_article(str, str) -> tuple[str, str]` used consistently across test fixture and implementation. `_fetch_full_law` returns `str` used by `_fetch_public_html` wrapper.
