"""Produce a deterministic inventory; flags are review hints, not patch instructions."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
import sys
import frontmatter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build import clean_body, content_kind, _body_hash


def inventory(today: date) -> dict:
    groups = {name: [] for name in ('not_regulation_text', 'truncated_summaries', 'empty_systems', 'empty_commodities', 'empty_vehicle_categories', 'future_in_force', 'prefix_region_mismatch', 'title_words_absent', 'summary_stale')}
    citations = defaultdict(list)
    records = []
    for path in sorted((ROOT / 'regulations').glob('*.md')):
        post = frontmatter.load(path)
        m = post.metadata
        rid = m['id']
        body = clean_body(post.content, str(m.get('source_api', '')))
        kind = content_kind(body)
        records.append({'id': rid, 'region': m['region'], 'source_api': m.get('source_api'), 'content_kind': kind, 'body_chars': len(body)})
        if kind != 'full': groups['not_regulation_text'].append({'id': rid, 'content_kind': kind})
        if str(m.get('summary', '')).rstrip().endswith(('...', '…')): groups['truncated_summaries'].append(rid)
        for field in ('systems', 'commodities', 'vehicle_categories'):
            if not m.get(field): groups['empty_' + field].append(rid)
        effective = m.get('effective_date')
        if effective and m.get('status') == 'in-force':
            try:
                if date.fromisoformat(str(effective)) > today: groups['future_in_force'].append({'id': rid, 'effective_date': str(effective)})
            except ValueError: pass
        if rid.split('-', 1)[0].upper() != m['region']: groups['prefix_region_mismatch'].append({'id': rid, 'region': m['region']})
        words = sorted(set(w.lower() for w in re.findall(r'[A-Za-z]{5,}', str(m.get('title', '')))))
        absent = [w for w in words if w not in body.lower()]
        if absent: groups['title_words_absent'].append({'id': rid, 'absent_words': absent, 'total_title_words': len(words)})
        if m.get('summary') and m.get('summary_hash') != _body_hash(body): groups['summary_stale'].append(rid)
        citations[str(m.get('citation', '')).strip().casefold()].append(rid)
    groups['duplicate_citations'] = [{'citation': c, 'ids': ids} for c, ids in sorted(citations.items()) if c and len(ids) > 1]
    return {'date': today.isoformat(), 'records_total': len(records), 'content_kinds': dict(Counter(r['content_kind'] for r in records)), 'counts': {k: len(v) for k, v in groups.items()}, 'lists': groups, 'records': records, 'limitations': ['content_kind full is a heuristic; it does not establish instrument identity, completeness or currency.', 'Title word absence includes translation, punctuation and editorial-title false positives.', 'Empty tags and duplicate citations can be legitimate; never patch automatically.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', type=date.fromisoformat, default=date.today())
    parser.add_argument('--out', type=Path, default=ROOT / 'review/inventory.json')
    args = parser.parse_args()
    result = inventory(args.date)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('records_total', 'content_kinds', 'counts')}))

if __name__ == '__main__': main()
