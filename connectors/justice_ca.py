"""Canada Justice Laws connector — pulls Motor Vehicle Safety Regulations (MVSR).

Uses the Justice Laws XML service: https://laws-lois.justice.gc.ca/eng/XML/
No API key required.  reg_id examples: "C.R.C.,_c._1038"
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

XML_BASE = "https://laws-lois.justice.gc.ca/eng/XML/{reg_id}.xml"
BROWSE_BASE = "https://laws-lois.justice.gc.ca/eng/regulations/{reg_id}/FullText.html"


def _ca_slug(reg_id: str, section: str | None = None) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]", "-", reg_id.lower()).strip("-")
    if section:
        sec_clean = re.sub(r"[^a-zA-Z0-9]", "-", section).strip("-")
        return f"ca-mvsr-{clean}-s{sec_clean}"
    return f"ca-mvsr-{clean}"


def _citation(reg_id: str, section: str | None = None) -> str:
    if section:
        return f"MVSR {reg_id} s. {section}"
    return f"MVSR {reg_id}"


def _source_url(reg_id: str) -> str:
    return BROWSE_BASE.format(reg_id=reg_id.replace(",_", ",_").replace(" ", "_"))


def _extract_section(root: ET.Element, section: str) -> tuple[str, str]:
    """Find a top-level Section by Label and return (title, markdown body)."""
    for sec_el in root.iter("Section"):
        label = sec_el.findtext("Label") or ""
        if label.strip() == section:
            headings = [h.text for h in sec_el.iter("TitleText") if h.text]
            title_suffix = headings[0].strip() if headings else ""
            title = f"MVSR s. {section}"
            if title_suffix:
                title = f"MVSR s. {section} — {title_suffix}"
            xml_str = ET.tostring(sec_el, encoding="unicode")
            md = markdownify(xml_str)
            md = re.sub(r"\n{3,}", "\n\n", md).strip()
            return title, md
    return f"MVSR s. {section}", ""


def _reg_title_from_xml(root: ET.Element) -> str:
    for tag in ["LongTitle", "ShortTitle", "Title"]:
        el = root.find(f".//{tag}")
        if el is not None and el.text:
            return el.text.strip()
    return ""


def _fetch_and_parse(session: RateLimitedSession, reg_id: str, section: str | None) -> tuple[str, str, ET.Element | None]:
    url = XML_BASE.format(reg_id=reg_id)
    resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"})
    xml_text = resp.content.decode("utf-8")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        root = None

    reg_title = _reg_title_from_xml(root) if root is not None else reg_id

    if section and root is not None:
        sec_title, md_body = _extract_section(root, section)
        if md_body:
            return sec_title, md_body, root

    # Fallback: convert full XML
    md_body = markdownify(xml_text)
    md_body = re.sub(r"\n{3,}", "\n\n", md_body).strip()
    title = f"MVSR {reg_id}" + (f" s. {section}" if section else "")
    if reg_title and not section:
        title = reg_title
    if not md_body:
        md_body = f"# {title}\n\nSee {_source_url(reg_id)} for full text."
    return title, md_body, root


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    records_conf: list[dict[str, Any]] = manifest.get("records", [])
    session = RateLimitedSession(rate=1.0)
    pulled: list[Path] = []
    failed: list[str] = []

    # Cache parsed XML roots by reg_id
    xml_cache: dict[str, tuple[str, ET.Element | None]] = {}

    for entry in records_conf:
        reg_id = str(entry.get("reg_id", "")).strip()
        section = str(entry.get("section", "")).strip() if entry.get("section") else None
        if not reg_id:
            continue

        label = f"CA MVSR {reg_id}" + (f" s.{section}" if section else "")
        try:
            print(f"  Pulling {label} ...", end=" ", flush=True)

            if reg_id not in xml_cache:
                title, md_body, xml_root = _fetch_and_parse(session, reg_id, section)
                xml_cache[reg_id] = (md_body if not section else "", xml_root)
            else:
                _, xml_root = xml_cache[reg_id]

            if section and xml_root is not None:
                title, md_body = _extract_section(xml_root, section)
                if not md_body:
                    title = f"MVSR {reg_id} s. {section}"
                    md_body = f"# {title}\n\nSee {_source_url(reg_id)} for full text."
            elif section:
                title = f"MVSR {reg_id} s. {section}"
                md_body = f"# {title}\n\nSee {_source_url(reg_id)} for full text."
            else:
                title, md_body, _ = _fetch_and_parse(session, reg_id, None)

            slug = _ca_slug(reg_id, section)
            citation = _citation(reg_id, section)
            src_url = _source_url(reg_id)

            record: dict[str, Any] = {
                "id": slug,
                "title": title,
                "region": "CA",
                "citation": citation,
                "status": "in-force",
                "source_url": src_url,
                "source_api": "justice_ca",
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
