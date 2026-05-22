from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
import requests
import yaml
from markdownify import markdownify as md

_DEFAULT_RATE = 5.0  # requests per second


class RateLimitedSession:
    def __init__(self, rate: float = _DEFAULT_RATE) -> None:
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "regulatory-repository/1.0 (+contact@example.com)"
        self._min_interval = 1.0 / rate
        self._last_call: float = 0.0

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        resp = self._session.get(url, timeout=30, **kwargs)
        self._last_call = time.monotonic()
        resp.raise_for_status()
        return resp

    def close(self) -> None:
        self._session.close()


def markdownify(html_or_xml: str) -> str:
    return md(html_or_xml, heading_style="ATX", bullets="-").strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


REQUIRED_FIELDS = {
    "id", "title", "region", "citation", "status",
    "source_url", "source_api", "tagging_status",
}


def validate_pulled(record: dict[str, Any]) -> None:
    missing = REQUIRED_FIELDS - record.keys()
    if missing:
        raise ValueError(f"record missing required fields: {sorted(missing)}")
    if record.get("region") not in {"US", "EU", "KR", "AU", "JP", "CA"}:
        raise ValueError(f"unknown region: {record.get('region')!r}")


def write_md(record: dict[str, Any], body: str, dest_dir: Path) -> Path:
    record = dict(record)
    record.setdefault("tagging_status", "untagged")
    record["last_pulled"] = _now_iso()
    validate_pulled(record)

    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{record['id']}.md"

    if path.exists():
        existing = frontmatter.load(path)
        existing_meta = dict(existing.metadata)
        for tag_field in ("commodities", "systems", "vehicle_categories", "tagging_status", "tagged_at"):
            if tag_field in existing_meta:
                record[tag_field] = existing_meta[tag_field]

    post = frontmatter.Post(body, **record)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return path
