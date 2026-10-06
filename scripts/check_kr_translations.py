"""Flag Korean (KMVSS) English translations that predate amendments in the current official text.

Resolves the version currently in force, fetches the full KMVSS from law.go.kr once, extracts each translated article's current Korean
text, and reports records whose Korean amendment dates (e.g. <개정 2026. 6. 5.>) are newer than
any YYYY-MM-DD date in the English translation.

Usage: python scripts/check_kr_translations.py
"""
from __future__ import annotations

import glob
import html as htmllib
import re
import sys
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from connectors._common import RateLimitedSession  # noqa: E402
from connectors.law_go_kr import _fetch_full_law, _parse_article_text, resolve_current_version  # noqa: E402

KO_DATE = re.compile(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.")
EN_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})|(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{4})")
MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def main() -> int:
    session = RateLimitedSession(rate=1)
    current = resolve_current_version(session, "270023")
    print(f"Checking against current version lsiSeq={current.get('lsiSeq')} (effective {current.get('efYd', '?')})")
    html = _fetch_full_law(session, "270023")
    plain = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", html)))
    stale = 0
    for path in sorted(glob.glob(str(ROOT / "regulations" / "kr-kmvss-art*.md"))):
        post = frontmatter.load(path)
        if post.metadata.get("translation_status") != "translated":
            continue
        article = post.metadata["id"].split("art", 1)[1]
        parsed = _parse_article_text(plain, article)
        if not parsed:
            print(f"NOT FOUND  {post.metadata['id']}")
            continue
        ko_dates = sorted({f"{a}-{int(b):02d}-{int(c):02d}" for a, b, c in KO_DATE.findall(parsed[1])})
        english = post.content.split("### Original text")[0]
        en_dates = set()
        for g in EN_DATE.findall(english):
            en_dates.add("-".join(g[:3]) if g[0] else f"{g[5]}-{MONTHS[g[4]]:02d}-{int(g[3]):02d}")
        missing = [d for d in ko_dates if d not in en_dates]
        if missing and ko_dates[-1] > max(en_dates, default=""):
            stale += 1
            print(f"STALE      {post.metadata['id']}  amendments not in translation: {', '.join(missing)}")
    print(f"{stale} stale translation(s)")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
