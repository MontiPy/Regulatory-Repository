"""eCFR connector — pulls 49 CFR regulations from the eCFR versioner API."""
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
TITLE = 49


def _get_latest_date(session: RateLimitedSession) -> str:
    resp = session.get(f"{API_BASE}/titles")
    data = resp.response.json() if hasattr(resp, "response") else resp.json() if hasattr(resp, "json") else {}
    titles = data.get("titles", [])
    t49 = next((t for t in titles if t.get("number") == TITLE), None)
    if t49:
        return t49["latest_issue_date"]
    raise RuntimeError(f"Title {TITLE} not found in eCFR titles endpoint")


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


def _get_latest_issue_date(session: _ECFRSession) -> str:
    resp = session.get_raw(f"{API_BASE}/titles")
    data = resp.json()
    titles = data.get("titles", [])
    t49 = next((t for t in titles if t.get("number") == TITLE), None)
    if t49:
        return t49["latest_issue_date"]
    raise RuntimeError(f"Title {TITLE} not found in eCFR titles endpoint")


def _section_url(part: int, section: int) -> str:
    return f"https://www.ecfr.gov/current/title-49/part-{part}/section-{part}.{section}"


def _part_url(part: int) -> str:
    return f"https://www.ecfr.gov/current/title-49/part-{part}"


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


def _fetch_section(session: _ECFRSession, issue_date: str, part: int, section: int) -> tuple[dict[str, Any], str]:
    section_str = f"{part}.{section}"
    url = f"{API_BASE}/full/{issue_date}/title-{TITLE}.xml"
    resp = session.get_raw(url, params={"part": str(part), "section": section_str})

    xml_text = resp.text
    md_body = _xml_to_md(xml_text)
    title_text = _parse_title_from_head(xml_text)

    if part == 571:
        citation = f"49 CFR §571.{section}"
        slug = f"us-fmvss-{section}"
        if not title_text:
            title_text = f"FMVSS Standard No. {section}"
    else:
        citation = f"49 CFR §{part}.{section}"
        slug = f"us-cfr{part}-{section}"
        if not title_text:
            title_text = f"49 CFR Part {part}, Section {section}"

    record: dict[str, Any] = {
        "id": slug,
        "title": title_text,
        "region": "US",
        "citation": citation,
        "status": "in-force",
        "source_url": _section_url(part, section),
        "source_api": "ecfr",
        "tagging_status": "untagged",
    }
    return record, md_body


def _fetch_part(session: _ECFRSession, issue_date: str, part: int) -> tuple[dict[str, Any], str]:
    url = f"{API_BASE}/full/{issue_date}/title-{TITLE}.xml"
    resp = session.get_raw(url, params={"part": str(part)})

    xml_text = resp.text
    md_body = _xml_to_md(xml_text)
    title_text = _parse_title_from_head(xml_text)

    if not title_text:
        title_text = f"49 CFR Part {part}"

    slug = f"us-cfr-part-{part}"
    citation = f"49 CFR Part {part}"

    record: dict[str, Any] = {
        "id": slug,
        "title": title_text,
        "region": "US",
        "citation": citation,
        "status": "in-force",
        "source_url": _part_url(part),
        "source_api": "ecfr",
        "tagging_status": "untagged",
    }
    return record, md_body


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    records_conf: list[dict[str, Any]] = manifest.get("records", [])
    session = _ECFRSession(rate=2.0)

    issue_date = _get_latest_issue_date(session)
    print(f"  eCFR issue date: {issue_date}")

    pulled: list[Path] = []
    failed: list[str] = []

    for entry in records_conf:
        part: int = entry["part"]
        section: int | None = entry.get("section")
        label = f"49 CFR Part {part}" + (f" §{part}.{section}" if section else "")
        try:
            print(f"  Pulling {label} ...", end=" ", flush=True)
            if section is not None:
                record, body = _fetch_section(session, issue_date, part, section)
            else:
                record, body = _fetch_part(session, issue_date, part)
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
