"""UN Regulation text via the Official Journal of the EU (fallback when unece.org blocks bots).

The EU publishes UN Regulations it applies in the OJ (CELEX sector 4, "42…X…"). This
connector finds, for each manifest regulation, the most recent OJ publication whose title
*is* that regulation (not an amendment or corrigendum), via the EU Publications Office
SPARQL endpoint, and pulls its HTML from EUR-Lex.

The OJ version can lag the latest UNECE supplement; the body says so and names the CELEX.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, markdownify, write_md
from connectors.eurlex import CELEX_HTML_URL, _extract_body_html
from connectors.unece import _citation, _ece_slug

SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"
QUERY = """PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?celex ?title ?date WHERE {
  ?w cdm:resource_legal_id_celex ?celex . FILTER(STRSTARTS(STR(?celex), "42"))
  ?e cdm:expression_belongs_to_work ?w ; cdm:expression_title ?title ;
     cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
  OPTIONAL { ?w cdm:work_date_document ?date }
  FILTER(REGEX(?title, "^(UN )?Regulation No", "i"))
}"""
MIN_CHARS = 3000


def oj_index() -> dict[str, list[tuple[str, str, str]]]:
    """Regulation number (e.g. '94', '13-H') -> [(date, celex, title)], newest first."""
    resp = requests.get(SPARQL, params={"query": QUERY, "format": "application/sparql-results+json"}, timeout=300)
    resp.raise_for_status()
    index: dict[str, list[tuple[str, str, str]]] = {}
    for b in resp.json()["results"]["bindings"]:
        title = b["title"]["value"]
        m = re.match(r"^(?:UN\s)?Regulation\s+No\.?\s*(\d+(?:-?[A-Z])?)\b", title, re.I)
        if not m:
            continue
        num = m.group(1).upper().replace("-", "")
        index.setdefault(num, []).append((b.get("date", {}).get("value", ""), b["celex"]["value"], title))
    for v in index.values():
        v.sort(reverse=True)
    return index


def _key(reg_num: Any) -> str:
    return str(reg_num).upper().replace("-", "")


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    print("  Querying EU Publications Office for OJ-published UN Regulations ...", flush=True)
    index = oj_index()
    print(f"  {len(index)} regulation numbers found in the OJ")
    session = RateLimitedSession(rate=0.5)
    pulled: list[Path] = []
    for entry in manifest.get("records", []):
        reg = entry.get("regulation")
        candidates = index.get(_key(reg), [])
        print(f"  UN R{reg}: {len(candidates)} OJ candidate(s) ...", end=" ", flush=True)
        for date, celex, oj_title in candidates:
            try:
                html = session.get(CELEX_HTML_URL.format(celex=celex)).content.decode("utf-8", errors="replace")
            except Exception as exc:  # noqa: BLE001
                print(f"[{celex} {exc}]", end=" ")
                continue
            body = re.sub(r"\n{3,}", "\n\n", markdownify(_extract_body_html(html))).strip()
            body = re.sub(r"!\[[^\]]*\]\(data:image/[^)]*\)", "*[Figure omitted — see the official source]*", body)
            if len(body) < MIN_CHARS:
                continue
            note = (
                f"> **Source:** text as published in the Official Journal of the European Union "
                f"(CELEX {celex}, {date or 'date n/a'}). Only the original UN/ECE texts have legal "
                f"effect, and later supplements or series of amendments may exist — check the "
                f"UNECE status document (ECE/TRANS/WP.29/343) for the current version.\n\n"
            )
            title = f"UN Regulation No. {reg} — {entry.get('title')}" if entry.get("title") else oj_title
            record = {
                "id": _ece_slug(reg), "title": title, "region": "ECE", "citation": _citation(reg),
                "status": "in-force", "source_url": CELEX_HTML_URL.format(celex=celex),
                "source_api": "unece", "tagging_status": "untagged",
            }
            pulled.append(write_md(record, note + body, dest_dir))
            print(f"OK {celex} ({len(body)} chars)")
            break
        else:
            print("no usable OJ text")
    session.close()
    return pulled
