"""Safety boundaries for a content review's machine-applied proposals."""
import importlib.util
import json
from pathlib import Path
import sys

import frontmatter
import pytest

from scripts import review_aggregate

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('review_apply_patches', ROOT / 'review/apply_patches.py')
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)


@pytest.mark.parametrize('value', ['2026-02-30', '2025-02-29', '2026-13-01', '2026-1-01'])
def test_patch_rejects_impossible_or_noncanonical_date(value):
    assert patcher.validate('effective_date', value)


def test_patch_allows_real_leap_day():
    assert patcher.validate('effective_date', '2024-02-29') is None


@pytest.mark.parametrize('value', ['https://', 'https:///example.gov', 'https://user:pass@example.gov', 'ftp://example.gov', 'https://example.gov/a b'])
def test_patch_rejects_invalid_or_credential_url(value):
    assert patcher.validate('source_url', value)


def test_machine_equivalent_and_body_edits_are_forbidden():
    assert patcher.validate('un_equivalent_ai', ['UN R94'])
    assert patcher.validate('body', 'replacement law')
    assert patcher.validate('un_equivalent', ['UN R13H']) is None
    assert patcher.validate('un_equivalent', ['R13-H'])


def test_stub_uses_corrected_title(tmp_path, monkeypatch):
    import apply_record_fixes
    monkeypatch.setattr(apply_record_fixes, 'REG', tmp_path)
    path = tmp_path / 'sample.md'
    path.write_text(frontmatter.dumps(frontmatter.Post('wrong topic', id='sample', title='Wrong title', source_api='spreadsheet')))
    apply_record_fixes.apply({'sample': {'title': 'Correct title', 'summary': 'Reference entry.', '_stub_body': True}}, 'test')
    post = frontmatter.load(path)
    assert post.content.startswith('# Correct title')
    assert 'wrong topic' not in post.content
    assert post.metadata['summary_hash']


def test_aggregate_separates_runs_and_requires_reviewed_coverage(tmp_path, monkeypatch):
    (tmp_path / 'shards').mkdir()
    (tmp_path / 'findings').mkdir()
    (tmp_path / 'coverage').mkdir()
    for name in ('old', 'current-one'):
        (tmp_path / 'shards' / (name + '.json')).write_text(json.dumps({'kind': 'records', 'items': ['a', 'b']}))
    findings = [{'id':'a', 'field':'summary', 'verdict':'wrong', 'severity':'medium', 'current':'A', 'proposed':'B', 'evidence':'clause', 'evidence_url':'regulations/a.md', 'confidence':'high'}]
    (tmp_path / 'findings/current-one.json').write_text(json.dumps(findings))
    (tmp_path / 'coverage/current-one.json').write_text(json.dumps({'reviewed':['a']}))
    out = tmp_path / 'result.json'
    monkeypatch.setattr(review_aggregate, 'REVIEW', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['review_aggregate', '--prefix', 'current-', '--coverage-dir', str(tmp_path/'coverage'), '--out', str(out)])
    assert review_aggregate.main() == 1
    result = json.loads(out.read_text())
    assert result['shards_total'] == 1
    assert result['coverage_gaps'] == {'current-one': ['b']}
    (tmp_path / 'coverage/current-one.json').write_text(json.dumps({'reviewed':['a','b']}))
    assert review_aggregate.main() == 0
    assert len(json.loads(out.read_text())['findings']) == 1


def test_knowledge_rejects_stale_and_path_traversal_edits():
    candidates, errors = patcher.prepare_knowledge([{'file':'../taxonomy.yaml', 'old':'regions:', 'new':'removed:', '_why':'test'}])
    assert not candidates and errors
    candidates, errors = patcher.prepare_knowledge([{'file':'glossary.yaml', 'old':'not present in current text', 'new':'changed', '_why':'test'}])
    assert not candidates and errors


def test_knowledge_schema_rejects_unknown_record_reference():
    raw = (ROOT / 'knowledge/crosswalk.yaml').read_text()
    old = 'records: [us-cfr-part-567, us-cfr-part-566]'
    assert raw.count(old) == 1
    candidates, errors = patcher.prepare_knowledge([{'file':'crosswalk.yaml', 'old':old, 'new':'records: [nonexistent-record]', '_why':'test'}])
    assert not candidates
    assert any('unknown record id' in e for e in errors)
    assert (ROOT / 'knowledge/crosswalk.yaml').read_text() == raw


def test_knowledge_validates_without_writing_candidate():
    path = ROOT / 'knowledge/glossary.yaml'
    raw = path.read_text()
    old = next(l for l in raw.splitlines() if l.startswith('  definition:'))
    new = old.replace('BEFORE sale', 'before sale')
    assert new != old
    candidates, errors = patcher.prepare_knowledge([{'file':'glossary.yaml','old':old,'new':new,'_why':'test'}])
    assert not errors
    assert candidates[path] == raw.replace(old, new, 1)
    assert path.read_text() == raw
