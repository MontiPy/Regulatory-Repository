"""Retain HTTP evidence for an external review, without editing the corpus.

Input is a JSON list of {url, ids, name?}. A bounded GET establishes retrieval
only, never legal accuracy. Use --retain for complete priority-source snapshots.
Incomplete, error, and challenge responses cannot count as legal evidence.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import io
import json
import re
import threading
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--retain", action="store_true")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--limit", type=int, default=131072)
    parser.add_argument("--timeout", type=int, default=18)
    args = parser.parse_args()
    entries = json.loads(args.input.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cache = args.cache or args.output.parent / "sources"
    cache.mkdir(parents=True, exist_ok=True)
    hosts = {urlparse(entry["url"]).hostname for entry in entries}
    locks = {host: threading.Semaphore(2) for host in hosts}

    def check(entry: dict) -> dict:
        url = entry["url"]
        row = {**{key: entry[key] for key in ("url", "ids", "name", "source_url", "as_of") if key in entry},
               "retrieved_at": datetime.now(timezone.utc).isoformat(),
               "legal_verification": "not_adjudicated"}
        key = re.sub(r"[^A-Za-z0-9_-]", "-", entry.get("name", "")) or hashlib.sha256(url.encode()).hexdigest()[:20]
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; RegulatoryRepositoryReview/1.0)"}
            headers.update({key: value for key, value in entry.get("headers", {}).items()
                            if key in {"Accept", "Accept-Language"}})
            row["request_headers"] = headers
            with locks[urlparse(url).hostname], requests.get(
                url, headers=headers,
                timeout=(8, args.timeout), stream=True,
            ) as response:
                row.update(status=response.status_code, final_url=response.url,
                           redirects=[{"url": r.url, "status": r.status_code} for r in response.history],
                           content_type=response.headers.get("Content-Type", ""),
                           last_modified=response.headers.get("Last-Modified"),
                           etag=response.headers.get("ETag"))
                data = bytearray()
                truncated = False
                for chunk in response.iter_content(16384):
                    data.extend(chunk)
                    if len(data) > args.limit:
                        truncated = True
                        del data[args.limit:]
                        break
                data = bytes(data)
                row.update(bytes_retained=len(data), truncated=truncated,
                           sha256=hashlib.sha256(data).hexdigest())
                text = ""
                if data.lstrip().startswith(b"<?xml") and "xhtml" not in row["content_type"]:
                    try:
                        document = ET.fromstring(data)
                        text = "\n".join("".join(node.itertext()).strip() for node in document.iter()
                                         if node.tag.rsplit("}", 1)[-1] in {"HEAD", "P", "FP", "AMDDATE", "CITA"})
                    except ET.ParseError:
                        row["extraction_error"] = "Incomplete or invalid XML"
                elif ("msword" not in row["content_type"] and not data.startswith(b"%PDF")):
                    soup = BeautifulSoup(data, "html.parser")
                    row["page_title"] = soup.title.get_text(" ", strip=True) if soup.title else ""
                    for tag in soup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    text = soup.get_text("\n", strip=True)
                challenge = re.search(
                    r"just a moment|verify (?:that )?you are human|access denied|request rejected|"
                    r"captcha|enable javascript and cookies|checking your browser|"
                    r"AWS WAF|Request unsuccessful\. Incapsula",
                    (row.get("page_title", "") + " " + text[:2500]), re.I,
                )
                error_page = re.fullmatch(r"error|page not found|404(?:.*)|service unavailable", row.get("page_title", ""), re.I)
                if challenge or (response.status_code == 202 and len(data) < 10000):
                    row["availability"] = "challenge_or_interstitial"
                elif response.status_code >= 400:
                    row["availability"] = "http_error"
                elif error_page:
                    row["availability"] = "source_error_page"
                elif not data:
                    row["availability"] = "empty_response"
                else:
                    row["availability"] = "response_retrieved"
                row["text_preview"] = re.sub(r"\s+", " ", text[:500])
                if args.retain or args.cache:
                    raw = cache / f"{key}.raw.gz"
                    raw.write_bytes(gzip.compress(data, mtime=0))
                    if args.retain and data.startswith(b"%PDF") and not truncated:
                        try:
                            from pdfminer.high_level import extract_text
                            text = extract_text(io.BytesIO(data))
                        except Exception as exc:
                            row["extraction_error"] = f"{type(exc).__name__}: {exc}"
                    if args.retain:
                        plain = cache / f"{key}.txt"
                        plain.write_text(text, encoding="utf-8")
                        row["text_path"] = str(plain)
                    row["raw_path"] = str(raw)
        except Exception as exc:
            row.update(availability="transport_error", error=f"{type(exc).__name__}: {exc}")
        return row

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(check, entry) for entry in entries]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            if len(results) % 25 == 0 or len(results) == len(entries):
                print(f"{len(results)}/{len(entries)}: {dict(Counter(r['availability'] for r in results))}", flush=True)
                args.output.write_text(json.dumps(sorted(results, key=lambda r: r["url"]), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
