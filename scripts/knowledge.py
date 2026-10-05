"""Load and validate the curated knowledge layer (knowledge/*.yaml).

Three hand-authored datasets sit on top of the pulled regulation corpus:

* ``knowledge/markets/*.yaml`` — one profile per market (certification regime,
  authorities, accepted approvals, marks, emissions level, process, …).
* ``knowledge/crosswalk.yaml`` — requirement topics × regulatory regimes, with the
  governing citation per regime and links to repository records.
* ``knowledge/glossary.yaml`` — certification / homologation terminology.

Everything here is validated strictly: unknown keys, bad enum values, duplicate
ids and — most importantly — references to record ids that do not exist in
``regulations/`` are build ERRORS, so a crosswalk link can never silently rot.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "knowledge"
MARKETS_DIR = KNOWLEDGE_DIR / "markets"
CROSSWALK_PATH = KNOWLEDGE_DIR / "crosswalk.yaml"
GLOSSARY_PATH = KNOWLEDGE_DIR / "glossary.yaml"

REGIMES = {
    "self-certification": "Self-certification",
    "type-approval": "Type approval",
    "hybrid": "Hybrid",
    "recognition": "Recognition",
    "registration-inspection": "Registration / inspection",
    "restricted": "Restricted",
}
REGIME_DESCRIPTIONS = {
    "self-certification": "Manufacturer certifies compliance itself; no pre-market government approval (enforced post-sale).",
    "type-approval": "Authority approves the vehicle type before sale, based on witnessed tests and conformity-of-production checks.",
    "hybrid": "National standards with a conformity certificate, where foreign test evidence (FMVSS / UN R) is accepted item by item.",
    "recognition": "Approvals granted elsewhere (EU WVTA, UN R, FMVSS, JP) are accepted as the basis for national registration.",
    "registration-inspection": "No whole-vehicle type approval — compliance is checked at import (pre-shipment inspection) or registration.",
    "restricted": "Sanctions or trade restrictions — do not engage without trade-compliance clearance.",
}
DRIVES = {"LHD", "RHD", "mixed"}
CONFIDENCE = {"high", "medium", "low"}
GROUPS = [
    "North America",
    "Central America & Caribbean",
    "South America",
    "Europe",
    "Eurasia",
    "Middle East",
    "Africa",
    "South Asia",
    "East Asia",
    "Southeast Asia",
    "Oceania",
]
CELL_STATUSES = {"mandatory", "phase-in", "proposed", "voluntary", "none"}
POWERTRAINS = ["ICE", "HEV", "PHEV", "BEV", "FCEV"]

MARKET_REQUIRED = {
    "code", "name", "group", "regions", "drive", "regime", "basis",
    "un_1958", "un_1998", "authorities", "accepts", "marks", "emissions",
    "language", "process", "records", "confidence",
}
MARKET_OPTIONAL = {"aliases", "members", "watch", "notes"}
MARKET_LISTS = {"regions", "authorities", "accepts", "marks", "process", "records",
                "aliases", "members", "watch", "notes"}
AUTHORITY_KEYS = {"name", "scope", "url"}

TOPIC_REQUIRED = {"id", "group", "title", "description", "powertrains", "cells"}
TOPIC_OPTIONAL = {"gtr"}
CELL_KEYS = {"cite", "records", "status", "note"}

GLOSSARY_REQUIRED = {"term", "definition"}
GLOSSARY_OPTIONAL = {"aka", "markets", "records"}


class KnowledgeError(Exception):
    pass


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("https://", "http://"))


def _check_records(where: str, records: Any, known_ids: set[str], errors: list[str]) -> list[str]:
    if records is None:
        return []
    if not isinstance(records, list):
        errors.append(f"{where}: records must be a list")
        return []
    for rid in records:
        if rid not in known_ids:
            errors.append(f"{where}: unknown record id '{rid}'")
    return [r for r in records if r in known_ids]


def load_markets(known_ids: set[str], known_regions: set[str], errors: list[str]) -> list[dict[str, Any]]:
    markets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(MARKETS_DIR.glob("*.yaml")):
        data = _load_yaml(path) or []
        if not isinstance(data, list):
            errors.append(f"{path.name}: top level must be a list of markets")
            continue
        for entry in data:
            code = (entry or {}).get("code", "?")
            where = f"{path.name}:{code}"
            if not isinstance(entry, dict):
                errors.append(f"{where}: market entry must be a mapping")
                continue
            missing = sorted(MARKET_REQUIRED - entry.keys())
            if missing:
                errors.append(f"{where}: missing keys {missing}")
            unknown = sorted(set(entry) - MARKET_REQUIRED - MARKET_OPTIONAL)
            if unknown:
                errors.append(f"{where}: unknown keys {unknown}")
            if code in seen:
                errors.append(f"{where}: duplicate market code")
            seen.add(code)
            for key in MARKET_LISTS & entry.keys():
                if not isinstance(entry[key], list):
                    errors.append(f"{where}: {key} must be a list")
                    entry[key] = []
            if entry.get("group") not in GROUPS:
                errors.append(f"{where}: group '{entry.get('group')}' not in {GROUPS}")
            if entry.get("regime") not in REGIMES:
                errors.append(f"{where}: regime '{entry.get('regime')}' not in {sorted(REGIMES)}")
            if entry.get("drive") not in DRIVES:
                errors.append(f"{where}: drive '{entry.get('drive')}' not in {sorted(DRIVES)}")
            if entry.get("confidence") not in CONFIDENCE:
                errors.append(f"{where}: confidence '{entry.get('confidence')}' not in {sorted(CONFIDENCE)}")
            for flag in ("un_1958", "un_1998"):
                if entry.get(flag) not in (True, False, None):
                    errors.append(f"{where}: {flag} must be true, false or null")
            for region in entry.get("regions", []):
                if region not in known_regions:
                    errors.append(f"{where}: region '{region}' not in taxonomy.regions")
            for auth in entry.get("authorities", []):
                if not isinstance(auth, dict) or set(auth) - AUTHORITY_KEYS or "name" not in auth:
                    errors.append(f"{where}: authority entries need name (+ optional scope, url): {auth!r}")
                    continue
                if "url" in auth and not _is_http_url(auth["url"]):
                    errors.append(f"{where}: authority url must be http(s): {auth['url']!r}")
            entry["records"] = _check_records(where, entry.get("records"), known_ids, errors)
            entry.setdefault("aliases", [])
            entry.setdefault("members", [])
            entry.setdefault("watch", [])
            entry.setdefault("notes", [])
            entry["regime_label"] = REGIMES.get(entry.get("regime"), entry.get("regime"))
            markets.append(entry)
    order = {g: i for i, g in enumerate(GROUPS)}
    markets.sort(key=lambda m: (order.get(m.get("group"), 99), str(m.get("name"))))
    return markets


def load_crosswalk(known_ids: set[str], market_codes: set[str], errors: list[str]) -> dict[str, Any]:
    data = _load_yaml(CROSSWALK_PATH) or {}
    columns = data.get("columns") or []
    groups = data.get("groups") or []
    topics = data.get("topics") or []
    col_keys: set[str] = set()
    for col in columns:
        key = col.get("key")
        if not key or key in col_keys:
            errors.append(f"crosswalk: column key missing or duplicate: {col!r}")
        col_keys.add(key)
        if col.get("market") not in market_codes:
            errors.append(f"crosswalk: column {key} references unknown market '{col.get('market')}'")
    seen: set[str] = set()
    for topic in topics:
        tid = topic.get("id", "?")
        where = f"crosswalk:{tid}"
        missing = sorted(TOPIC_REQUIRED - topic.keys())
        if missing:
            errors.append(f"{where}: missing keys {missing}")
        unknown = sorted(set(topic) - TOPIC_REQUIRED - TOPIC_OPTIONAL)
        if unknown:
            errors.append(f"{where}: unknown keys {unknown}")
        if tid in seen:
            errors.append(f"{where}: duplicate topic id")
        seen.add(tid)
        if topic.get("group") not in groups:
            errors.append(f"{where}: group '{topic.get('group')}' not declared in groups")
        powertrains = topic.get("powertrains") or []
        if powertrains == ["all"]:
            topic["powertrains"] = list(POWERTRAINS)
        else:
            for pt in powertrains:
                if pt not in POWERTRAINS:
                    errors.append(f"{where}: powertrain '{pt}' not in {POWERTRAINS} (or [all])")
        cells = topic.get("cells") or {}
        for key, cell in cells.items():
            cwhere = f"{where}.{key}"
            if key not in col_keys:
                errors.append(f"{cwhere}: unknown column")
                continue
            if not isinstance(cell, dict) or not cell.get("cite"):
                errors.append(f"{cwhere}: cell needs a non-empty cite")
                continue
            extra = sorted(set(cell) - CELL_KEYS)
            if extra:
                errors.append(f"{cwhere}: unknown cell keys {extra}")
            status = cell.setdefault("status", "mandatory")
            if status not in CELL_STATUSES:
                errors.append(f"{cwhere}: status '{status}' not in {sorted(CELL_STATUSES)}")
            cell["records"] = _check_records(cwhere, cell.get("records"), known_ids, errors)
    return {
        "reviewed": str(data.get("reviewed", "")),
        "columns": columns,
        "groups": groups,
        "powertrains": POWERTRAINS,
        "topics": topics,
    }


def load_glossary(known_ids: set[str], market_codes: set[str], errors: list[str]) -> list[dict[str, Any]]:
    data = _load_yaml(GLOSSARY_PATH) or []
    terms: list[dict[str, Any]] = []
    for entry in data:
        term = (entry or {}).get("term", "?")
        where = f"glossary:{term}"
        missing = sorted(GLOSSARY_REQUIRED - entry.keys())
        if missing:
            errors.append(f"{where}: missing keys {missing}")
        unknown = sorted(set(entry) - GLOSSARY_REQUIRED - GLOSSARY_OPTIONAL)
        if unknown:
            errors.append(f"{where}: unknown keys {unknown}")
        for code in entry.get("markets", []) or []:
            if code not in market_codes:
                errors.append(f"{where}: unknown market code '{code}'")
        entry["records"] = _check_records(where, entry.get("records"), known_ids, errors)
        entry.setdefault("aka", [])
        entry.setdefault("markets", [])
        terms.append(entry)
    terms.sort(key=lambda t: str(t.get("term", "")).lower())
    return terms


def build_knowledge(known_ids: set[str], known_regions: set[str]) -> tuple[dict[str, Any], list[str]]:
    """Return ({markets, crosswalk, glossary}, errors)."""
    errors: list[str] = []
    markets = load_markets(known_ids, known_regions, errors)
    codes = {m["code"] for m in markets}
    crosswalk = load_crosswalk(known_ids, codes, errors)
    glossary = load_glossary(known_ids, codes, errors)
    payload = {
        "markets": {"groups": GROUPS, "regimes": REGIMES, "regime_descriptions": REGIME_DESCRIPTIONS, "markets": markets},
        "crosswalk": crosswalk,
        "glossary": glossary,
    }
    return payload, errors
