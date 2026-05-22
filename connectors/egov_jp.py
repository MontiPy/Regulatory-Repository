"""Japan e-Gov Law API connector — pulls Safety Regulations for Road Vehicles (道路運送車両の保安基準).

Uses the e-Gov Law API v1: https://laws.e-gov.go.jp/api/1/lawdata/{lawId}
No API key required. Returns full-law XML; we extract the requested article.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, markdownify, write_md

API_BASE = "https://laws.e-gov.go.jp/api/1/lawdata"


def _jp_slug(law_id: str, article: str) -> str:
    article_slug = re.sub(r"[^a-zA-Z0-9]", "-", article).strip("-")
    return f"jp-jvsregs-art{article_slug}"


def _citation(article: str) -> str:
    return f"JVSR Article {article}"


def _source_url(law_id: str) -> str:
    return f"https://laws.e-gov.go.jp/law/{law_id}"


def _article_matches(xml_num: str, requested: str) -> bool:
    """Match article numbers tolerating hyphen/underscore notation for sub-articles.

    e-Gov XML stores sub-articles as "11_2" (underscore) for 第11条の2, but
    manifests and references commonly use "11-2" (hyphen). Accept either form.
    """
    try:
        return int(xml_num) == int(requested)
    except ValueError:
        pass
    if xml_num == requested:
        return True
    return xml_num.replace("_", "-") == requested.replace("_", "-")


def _law_xml_to_article(xml_text: str, article_num: str) -> tuple[str, str]:
    """Extract a specific article from e-Gov v1 XML and return (title, markdown)."""
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        return "", ""

    law_title_el = root.find(".//LawTitle")
    law_title = law_title_el.text.strip() if law_title_el is not None and law_title_el.text else "JVSR"

    # Find the Article element with Num matching article_num
    target_article = None
    for article_el in root.iter("Article"):
        num = article_el.get("Num", "").strip()
        if _article_matches(num, article_num):
            target_article = article_el
            break

    if target_article is None:
        return "", ""

    caption_el = target_article.find("ArticleCaption")
    caption = caption_el.text.strip() if caption_el is not None and caption_el.text else ""

    article_xml = ET.tostring(target_article, encoding="unicode")
    md_body = markdownify(article_xml)
    md_body = re.sub(r"\n{3,}", "\n\n", md_body).strip()

    title = f"JVSR Article {article_num}"
    if caption:
        title = f"JVSR Article {article_num} — {caption}"

    return title, md_body


def _fetch_law(session: RateLimitedSession, law_id: str) -> str:
    """Fetch full law XML via e-Gov v1 API."""
    url = f"{API_BASE}/{law_id}"
    resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"})
    return resp.text


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    records_conf: list[dict[str, Any]] = manifest.get("records", [])
    session = RateLimitedSession(rate=1.0)
    pulled: list[Path] = []
    failed: list[str] = []

    # Cache law XML by law_id to avoid re-fetching the same large document
    law_xml_cache: dict[str, str] = {}

    for entry in records_conf:
        law_id = str(entry.get("law_id", "")).strip()
        article = str(entry.get("article", "")).strip()
        if not law_id or not article:
            continue

        label = f"JP law {law_id} Article {article}"
        try:
            print(f"  Pulling {label} ...", end=" ", flush=True)

            if law_id not in law_xml_cache:
                law_xml_cache[law_id] = _fetch_law(session, law_id)

            xml_text = law_xml_cache[law_id]
            title, md_body = _law_xml_to_article(xml_text, article)

            if not title:
                title = f"JVSR Article {article}"
            if not md_body:
                md_body = f"# {title}\n\nSee {_source_url(law_id)} for full text."

            slug = _jp_slug(law_id, article)
            citation = _citation(article)
            src_url = _source_url(law_id)

            record: dict[str, Any] = {
                "id": slug,
                "title": title,
                "region": "JP",
                "citation": citation,
                "status": "in-force",
                "source_url": src_url,
                "source_api": "egov_jp",
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
