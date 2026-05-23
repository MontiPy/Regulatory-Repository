"""law.go.kr connector — pulls Korean motor vehicle safety standards (KMVSS).

Requires a free API key from https://open.law.go.kr — set KR_LAW_API_KEY env var.
Without a key, this connector falls back to scraping the public HTML pages.
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
_law_html_cache: dict[str, str] = {}


def _kr_slug(law_id: str, article: str) -> str:
    return f"kr-kmvss-art{article}"


def _citation(law_id: str, article: str) -> str:
    return f"KMVSS Article {article}"


def _source_url(law_id: str, article: str) -> str:
    return f"https://law.go.kr/LSW/lsInfoP.do?lsiSeq={law_id}#AJAX"


def _article_label_pattern(article: str) -> re.Pattern[str]:
    if "-" in article:
        base, sub = article.split("-", 1)
        pat = rf"제\s*{re.escape(base)}\s*조의\s*{re.escape(sub)}(?!\d)"
    else:
        pat = rf"제\s*{re.escape(article)}\s*조\b"
    return re.compile(pat)


def _parse_article(full_html: str, article: str) -> tuple[str, str]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(full_html, "html.parser")
    pattern = _article_label_pattern(article)

    label = None
    for lbl in soup.find_all("label"):
        if pattern.search(lbl.get_text()):
            label = lbl
            break

    if label is None:
        return f"KMVSS Article {article}", f"# KMVSS Article {article}\n\nSee source for full text."

    title_text = f"KMVSS Article {article} — {label.get_text(strip=True)}"
    container = label.find_parent("p")
    if container is None:
        return title_text, f"# {title_text}\n\nSee source for full text."

    fragments: list[str] = [str(container)]
    for sib in container.next_siblings:
        tag = getattr(sib, "name", None)
        cls = (sib.get("class") or []) if hasattr(sib, "get") else []
        if "pty1_p4" in cls:
            break
        if tag in ("div", "table", "footer", "script", "style"):
            break
        fragments.append(str(sib))

    body_md = markdownify("".join(fragments))
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()
    return title_text, body_md or f"# {title_text}\n\nSee source for full text."


def _discover_params(session: RateLimitedSession, law_id: str) -> dict[str, str]:
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
    if law_id in _law_html_cache:
        return _law_html_cache[law_id]
    params = _discover_params(session, law_id)
    resp = session.get(BODY_URL, params=params)
    html = resp.text
    if 'class="pty1_p4"' not in html and "pty1_p4" not in html:
        raise RuntimeError(
            f"lsInfoR.do response for lsiSeq={law_id} contains no article blocks. "
            f"Params used: {params}. First 500 chars: {html[:500]}"
        )
    _law_html_cache[law_id] = html
    return html


def _fetch_with_api(session: RateLimitedSession, api_key: str, law_id: str, article: str) -> tuple[str, str]:
    params = {
        "OC": api_key,
        "target": "article",
        "type": "JSON",
        "lawId": law_id,
        "artNo": article,
    }
    resp = session.get(API_BASE, params=params)
    data = resp.json() if hasattr(resp, "json") else {}
    article_data = data.get("LawService", {}).get("law", {}).get("article", [])
    if isinstance(article_data, list) and article_data:
        item = article_data[0]
    elif isinstance(article_data, dict):
        item = article_data
    else:
        item = {}

    title = item.get("articleTitle", "") or f"KMVSS Article {article}"
    content = item.get("articleContent", "") or ""
    md_body = markdownify(content) if content else f"# {title}\n\nSee source for full text."
    return title, md_body


def _fetch_public_html(session: RateLimitedSession, law_id: str, article: str) -> tuple[str, str]:
    url = f"{PUBLIC_BASE}/LSW/lsInfoP.do?lsiSeq={law_id}"
    try:
        resp = session.get(url)
        html = resp.text
        title = f"KMVSS Article {article}"
        match = re.search(rf"<span[^>]*>\s*제\s*{article}\s*조\s*</span>\s*<span[^>]*>(.*?)</span>", html, re.DOTALL)
        if match:
            title_raw = re.sub(r"<[^>]+>", "", match.group(1))
            title = f"KMVSS Article {article} — {title_raw.strip()}"
        md_body = markdownify(html)
        md_body = re.sub(r"\n{3,}", "\n\n", md_body).strip()
        if not md_body:
            md_body = f"# {title}\n\nSee {_source_url(law_id, article)} for full text."
    except Exception:
        title = f"KMVSS Article {article}"
        md_body = f"# {title}\n\nSee {_source_url(law_id, article)} for full text."
    return title, md_body


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    records_conf: list[dict[str, Any]] = manifest.get("records", [])
    api_key = os.environ.get("KR_LAW_API_KEY", "").strip()

    if not api_key:
        print("  NOTE: KR_LAW_API_KEY not set. Using public HTML fallback (limited content).")

    session = RateLimitedSession(rate=1.0)
    pulled: list[Path] = []
    failed: list[str] = []

    for entry in records_conf:
        law_id = str(entry.get("law_id", "")).strip()
        article = str(entry.get("article", "")).strip()
        if not law_id or not article:
            continue

        label = f"KR law {law_id} Article {article}"
        try:
            print(f"  Pulling {label} ...", end=" ", flush=True)

            if api_key:
                title, md_body = _fetch_with_api(session, api_key, law_id, article)
            else:
                title, md_body = _fetch_public_html(session, law_id, article)

            slug = _kr_slug(law_id, article)
            citation = _citation(law_id, article)
            src_url = _source_url(law_id, article)

            record: dict[str, Any] = {
                "id": slug,
                "title": title,
                "region": "KR",
                "citation": citation,
                "status": "in-force",
                "source_url": src_url,
                "source_api": "law_go_kr",
                "tagging_status": "untagged",
            }
            path = write_md(record, md_body, dest_dir)
            pulled.append(path)
            print(f"OK -> {path.name}")
        except Exception as exc:
            print(f"FAILED: {exc}")
            failed.append(f"{label}: {exc}")

    session.close()

    if failed:
        print(f"\n{len(failed)} failure(s):")
        for msg in failed:
            print(f"  {msg}")

    return pulled
