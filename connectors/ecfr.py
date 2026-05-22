"""eCFR connector — pulls CFR regulations from the eCFR versioner API.

Manifest entries for 49 CFR (default title):
  - { part: 571, section: 108 }        # FMVSS section
  - { part: 565 }                       # full 49 CFR part

Manifest entries for other CFR titles:
  - { title: 40, part: 86 }             # 40 CFR Part 86 (EPA emissions)
  - { title: 40, part: 600 }            # 40 CFR Part 600 (fuel economy/GHG)
  - { title: 47, part: 15 }             # 47 CFR Part 15 (FCC radio devices)
  - { title: 40, part: 86, section: "1811-27" }  # specific section
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, write_md

API_BASE = "https://www.ecfr.gov/api/versioner/v1"
DEFAULT_TITLE = 49


class _ECFRSession(RateLimitedSession):
    """Thin extension that exposes the raw requests.Response."""

    def get_raw(self, url: str, **kwargs: Any):  # noqa: ANN001
        import time
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        resp = self._session.get(url, timeout=30, **kwargs)
        self._last_call = time.monotonic()
        resp.raise_for_status()
        return resp


def _get_latest_issue_date(session: _ECFRSession, title: int) -> str:
    resp = session.get_raw(f"{API_BASE}/titles")
    data = resp.json()
    titles = data.get("titles", [])
    t = next((t for t in titles if t.get("number") == title), None)
    if t:
        return t["latest_issue_date"]
    raise RuntimeError(f"Title {title} not found in eCFR titles endpoint")


def _section_url(title: int, part: int, section: Any) -> str:
    return f"https://www.ecfr.gov/current/title-{title}/part-{part}/section-{part}.{section}"


def _part_url(title: int, part: int) -> str:
    return f"https://www.ecfr.gov/current/title-{title}/part-{part}"


def _xml_to_md(xml_text: str) -> str:
    """Convert eCFR XML (DIV8/DIV5 etc.) to clean Markdown."""
    lines: list[str] = []

    def _all_text(elem: ET.Element) -> str:
        return "".join(elem.itertext()).strip()

    def _walk(elem: ET.Element, depth: int) -> None:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "HEAD":
            text = _all_text(elem)
            hashes = "#" * min(max(depth, 1), 6)
            lines.append(f"\n{hashes} {text}\n")
            return

        if tag in ("P", "FP", "AMDDATE"):
            text = _all_text(elem)
            if text:
                lines.append(f"\n{text}\n")
            return

        if tag == "CITA":
            text = _all_text(elem)
            if text:
                lines.append(f"\n*{text}*\n")
            return

        if tag in ("TABLE",):
            lines.append(f"\n[Table — see source for details]\n")
            return

        if tag in ("E", "I", "SU"):
            return

        for child in elem:
            _walk(child, depth + 1)

    try:
        root = ET.fromstring(xml_text)
        _walk(root, 1)
    except ET.ParseError:
        return xml_text[:5000]

    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _parse_title_from_head(xml_text: str) -> str:
    try:
        root = ET.fromstring(xml_text)
        head = root.find("HEAD")
        if head is not None:
            return "".join(head.itertext()).strip()
        head = root.find(".//HEAD")
        if head is not None:
            return "".join(head.itertext()).strip()
    except ET.ParseError:
        pass
    return ""


def _make_slug(title: int, part: int, section: Any | None) -> str:
    if title == DEFAULT_TITLE:
        if part == 571:
            return f"us-fmvss-{section}"
        if section is not None:
            return f"us-cfr{part}-{section}"
        return f"us-cfr-part-{part}"
    # Non-default title (40 CFR, 47 CFR, etc.)
    if section is not None:
        return f"us-{title}cfr{part}-{section}"
    return f"us-{title}cfr-part-{part}"


def _make_citation(title: int, part: int, section: Any | None) -> str:
    if section is not None:
        return f"{title} CFR §{part}.{section}"
    return f"{title} CFR Part {part}"


def _make_fallback_title(title: int, part: int, section: Any | None) -> str:
    if title == DEFAULT_TITLE and part == 571:
        return f"FMVSS Standard No. {section}" if section else f"FMVSS Part {part}"
    if section is not None:
        return f"{title} CFR §{part}.{section}"
    return f"{title} CFR Part {part}"


def _fetch_section(session: _ECFRSession, issue_date: str, title: int, part: int, section: Any) -> tuple[dict[str, Any], str]:
    section_str = f"{part}.{section}"
    url = f"{API_BASE}/full/{issue_date}/title-{title}.xml"
    resp = session.get_raw(url, params={"part": str(part), "section": section_str})

    xml_text = resp.content.decode("utf-8")
    md_body = _xml_to_md(xml_text)
    title_text = _parse_title_from_head(xml_text) or _make_fallback_title(title, part, section)

    record: dict[str, Any] = {
        "id": _make_slug(title, part, section),
        "title": title_text,
        "region": "US",
        "citation": _make_citation(title, part, section),
        "status": "in-force",
        "source_url": _section_url(title, part, section),
        "source_api": "ecfr",
        "tagging_status": "untagged",
    }
    return record, md_body


def _fetch_part(session: _ECFRSession, issue_date: str, title: int, part: int) -> tuple[dict[str, Any], str]:
    url = f"{API_BASE}/full/{issue_date}/title-{title}.xml"
    resp = session.get_raw(url, params={"part": str(part)})

    xml_text = resp.content.decode("utf-8")
    md_body = _xml_to_md(xml_text)
    title_text = _parse_title_from_head(xml_text) or _make_fallback_title(title, part, None)

    record: dict[str, Any] = {
        "id": _make_slug(title, part, None),
        "title": title_text,
        "region": "US",
        "citation": _make_citation(title, part, None),
        "status": "in-force",
        "source_url": _part_url(title, part),
        "source_api": "ecfr",
        "tagging_status": "untagged",
    }
    return record, md_body


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    records_conf: list[dict[str, Any]] = manifest.get("records", [])
    session = _ECFRSession(rate=2.0)

    # Fetch issue dates per title (cached — only one API call per unique title)
    issue_dates: dict[int, str] = {}

    def get_issue_date(title: int) -> str:
        if title not in issue_dates:
            issue_dates[title] = _get_latest_issue_date(session, title)
            print(f"  eCFR issue date (title {title}): {issue_dates[title]}")
        return issue_dates[title]

    pulled: list[Path] = []
    failed: list[str] = []

    for entry in records_conf:
        title: int = int(entry.get("title", DEFAULT_TITLE))
        part: int = entry["part"]
        section: Any = entry.get("section")
        label = f"{title} CFR Part {part}" + (f" §{part}.{section}" if section else "")
        try:
            print(f"  Pulling {label} ...", end=" ", flush=True)
            issue_date = get_issue_date(title)
            if section is not None:
                record, body = _fetch_section(session, issue_date, title, part, section)
            else:
                record, body = _fetch_part(session, issue_date, title, part)
            path = write_md(record, body, dest_dir)
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
