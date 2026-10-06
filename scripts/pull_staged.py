"""Pull one region into a staging directory (never touches regulations/).

Usage: python scripts/pull_staged.py REGION STAGE_DIR
Then merge with: python scripts/merge_staged.py STAGE_DIR [--apply]
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from pull import REGION_CONNECTOR  # noqa: E402

region, stage = sys.argv[1], Path(sys.argv[2])
module_name, manifest_rel = REGION_CONNECTOR[region]
out = stage / region
out.mkdir(parents=True, exist_ok=True)
paths = importlib.import_module(module_name).pull(ROOT / manifest_rel, out)
print(f"{region}: {len(paths)} written to {out}")
