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


def _kr_slug(law_id: str, article: str) -> str:
    return f"kr-kmvss-art{article}"


def _citation(law_id: str, article: str) -> str:
    return f"KMVSS Article {article}"


def _source_url(law_id: str, article: str) -> str:
    return f"https://law.go.kr/LSW/lsInfoP.do?lsiSeq={law_id}#AJAX"


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
