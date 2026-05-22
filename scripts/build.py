from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

import bleach
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"
TEMPLATES_DIR = ROOT / "templates"
DIST_DIR = ROOT / "dist"
TAXONOMY_PATH = ROOT / "taxonomy.yaml"
REPORT_PATH = ROOT / ".build_report.txt"

REQUIRED_KEYS = {
    "id",
    "title",
    "region",
    "citation",
    "status",
    "source_url",
    "source_api",
    "last_pulled",
    "tagging_status",
}

OPTIONAL_KEYS = {
    "aliases",
    "commodities",
    "systems",
    "vehicle_categories",
    "un_equivalent",
    "related",
    "tags",
    "tagged_at",
    "effective_date",
    "last_amended",
}

ALLOWED_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS

TAXONOMY_FIELDS = {
    "region": "regions",
    "status": "statuses",
    "tagging_status": "tagging_statuses",
    "commodities": "commodities",
    "systems": "systems",
    "vehicle_categories": "vehicle_categories",
}

LIST_FIELDS = {
    "aliases",
    "commodities",
    "systems",
    "vehicle_categories",
    "un_equivalent",
    "related",
    "tags",
}

UN_EQUIVALENT_RE = re.compile(r"^UN R\d+[a-z]?$")

ALLOWED_TAGS = [
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "ul",
    "ol",
    "li",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "pre",
    "code",
    "blockquote",
    "strong",
    "em",
    "a",
    "br",
    "hr",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
}


class BuildIssue:
    def __init__(self, severity: str, message: str) -> None:
        self.severity = severity
        self.message = message

    def __str__(self) -> str:
        return f"{self.severity}: {self.message}"


def load_taxonomy() -> tuple[dict[str, list[str]], dict[str, set[str]]]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    taxonomy = {key: list(value or []) for key, value in raw.items()}
    taxonomy_sets = {key: set(values) for key, values in taxonomy.items()}
    return taxonomy, taxonomy_sets


def as_list(value: Any, field: str, issues: list[BuildIssue]) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    issues.append(BuildIssue("ERROR", f"{field} must be a list"))
    return []


def stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def validate_required(
    metadata: dict[str, Any],
    path: Path,
    issues: list[BuildIssue],
) -> None:
    missing = sorted(REQUIRED_KEYS - metadata.keys())
    if missing:
        issues.append(BuildIssue("ERROR", f"missing required fields: {', '.join(missing)}"))

    unknown = sorted(set(metadata.keys()) - ALLOWED_KEYS)
    if unknown:
        issues.append(BuildIssue("ERROR", f"unknown frontmatter keys: {', '.join(unknown)}"))

    record_id = metadata.get("id")
    if record_id is not None and record_id != path.stem:
        issues.append(BuildIssue("ERROR", f"id '{record_id}' must match filename stem '{path.stem}'"))


def validate_taxonomy(
    metadata: dict[str, Any],
    taxonomy_sets: dict[str, set[str]],
    issues: list[BuildIssue],
    draft: bool,
) -> None:
    severity = "WARN" if draft else "ERROR"

    for field, taxonomy_key in TAXONOMY_FIELDS.items():
        if field not in metadata:
            continue
        allowed = taxonomy_sets.get(taxonomy_key, set())
        values = as_list(metadata[field], field, issues) if field in LIST_FIELDS else [metadata[field]]
        for value in values:
            if value not in allowed:
                issues.append(BuildIssue(severity, f"{field} value '{value}' is not in taxonomy.{taxonomy_key}"))


def validate_un_equivalent(metadata: dict[str, Any], issues: list[BuildIssue]) -> None:
    for value in as_list(metadata.get("un_equivalent"), "un_equivalent", issues):
        if not isinstance(value, str) or not UN_EQUIVALENT_RE.match(value):
            issues.append(BuildIssue("ERROR", f"un_equivalent value '{value}' must match ^UN R\\d+[a-z]?$"))


def validate_list_fields(metadata: dict[str, Any], issues: list[BuildIssue]) -> None:
    for field in LIST_FIELDS:
        if field in metadata:
            as_list(metadata[field], field, issues)


def render_markdown(body: str) -> str:
    import markdown

    raw_html = markdown.markdown(body, extensions=["extra", "tables"])
    return bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )


def summarize(body_html: str) -> str:
    plain = bleach.clean(body_html, tags=[], strip=True)
    plain = unescape(re.sub(r"\s+", " ", plain)).strip()
    if len(plain) <= 250:
        return plain
    cutoff = plain.rfind(" ", 0, 250)
    if cutoff < 180:
        cutoff = 250
    return plain[:cutoff].rstrip() + "..."


def build_record(path: Path, taxonomy_sets: dict[str, set[str]], draft: bool) -> tuple[dict[str, Any], list[BuildIssue]]:
    import frontmatter

    post = frontmatter.load(path)
    metadata = dict(post.metadata)
    issues: list[BuildIssue] = []

    validate_required(metadata, path, issues)
    validate_list_fields(metadata, issues)
    validate_taxonomy(metadata, taxonomy_sets, issues, draft)
    validate_un_equivalent(metadata, issues)

    body_html = render_markdown(post.content)
    record = {
        "id": stringify(metadata.get("id")),
        "title": stringify(metadata.get("title")),
        "region": stringify(metadata.get("region")),
        "citation": stringify(metadata.get("citation")),
        "status": stringify(metadata.get("status")),
        "source_url": stringify(metadata.get("source_url")),
        "source_api": stringify(metadata.get("source_api")),
        "last_pulled": stringify(metadata.get("last_pulled")),
        "tagging_status": stringify(metadata.get("tagging_status")),
        "tagged_at": stringify(metadata.get("tagged_at")),
        "aliases": as_list(metadata.get("aliases"), "aliases", []),
        "commodities": as_list(metadata.get("commodities"), "commodities", []),
        "systems": as_list(metadata.get("systems"), "systems", []),
        "vehicle_categories": as_list(metadata.get("vehicle_categories"), "vehicle_categories", []),
        "un_equivalent": as_list(metadata.get("un_equivalent"), "un_equivalent", []),
        "related": as_list(metadata.get("related"), "related", []),
        "tags": as_list(metadata.get("tags"), "tags", []),
        "body_html": body_html,
        "summary_text": summarize(body_html),
    }
    return record, issues


def warn_for_missing_related(records: list[dict[str, Any]], issues_by_id: dict[str, list[BuildIssue]]) -> None:
    known_ids = {record["id"] for record in records if record.get("id")}
    for record in records:
        record_id = record.get("id")
        if not record_id:
            continue
        for related_id in record.get("related", []):
            if related_id not in known_ids:
                issues_by_id[record_id].append(BuildIssue("WARN", f"related id '{related_id}' was not found"))


def report_line(record: dict[str, Any], issues: list[BuildIssue]) -> str:
    status = "ERROR" if any(issue.severity == "ERROR" for issue in issues) else "WARN" if issues else "OK"
    label = record.get("id") or "(missing id)"
    if not issues:
        return f"{status} {label}"
    detail = "; ".join(str(issue) for issue in issues)
    return f"{status} {label} - {detail}"


def render_index(records: list[dict[str, Any]], taxonomy: dict[str, list[str]]) -> None:
    records_json = json.dumps(records, ensure_ascii=False).replace("</", "<\\/")
    taxonomy_json = json.dumps(taxonomy, ensure_ascii=False).replace("</", "<\\/")
    region_counts = dict(Counter(record["region"] for record in records if record.get("region")))
    tagging_status_counts = dict(Counter(record["tagging_status"] for record in records if record.get("tagging_status")))
    build_meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(records),
        "region_counts": region_counts,
        "tagging_status_counts": tagging_status_counts,
    }

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("index.html.j2")
    html = template.render(
        records_json=records_json,
        taxonomy=taxonomy_json,
        build_meta=build_meta,
    )
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "index.html").write_text(html, encoding="utf-8")


def build(draft: bool) -> int:
    taxonomy, taxonomy_sets = load_taxonomy()
    entries: list[tuple[dict[str, Any], list[BuildIssue]]] = []

    for path in sorted(REGULATIONS_DIR.glob("*.md")):
        record, issues = build_record(path, taxonomy_sets, draft)
        entries.append((record, issues))

    records = [record for record, _issues in entries]
    issues_by_id = {record["id"]: issues for record, issues in entries if record.get("id")}
    warn_for_missing_related(records, issues_by_id)
    entries.sort(key=lambda item: (item[0].get("region", ""), item[0].get("citation", "")))
    records = [record for record, _issues in entries]

    report_lines = [report_line(record, issues) for record, issues in entries]
    REPORT_PATH.write_text("\n".join(report_lines) + ("\n" if report_lines else ""), encoding="utf-8")
    render_index(records, taxonomy)

    error_count = sum(
        1
        for _record, issues in entries
        for issue in issues
        if issue.severity == "ERROR"
    )
    warning_count = sum(
        1
        for _record, issues in entries
        for issue in issues
        if issue.severity == "WARN"
    )
    print(
        f"Build complete: {len(records)} records, "
        f"{error_count} errors, {warning_count} warnings. "
        f"Wrote dist/index.html and .build_report.txt."
    )
    return 1 if error_count else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the offline regulatory repository index.")
    parser.add_argument("--draft", action="store_true", help="Downgrade taxonomy facet errors to warnings.")
    args = parser.parse_args()
    return build(draft=args.draft)


if __name__ == "__main__":
    sys.exit(main())
