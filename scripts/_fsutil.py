"""Filesystem utilities shared across build and tagging scripts.

OneDrive-mounted folders on Windows use reparse points that cause
Path.glob to silently return nothing. Use list_md_files() instead of
directory.glob("*.md") everywhere in this project.
"""
from __future__ import annotations

import platform
import subprocess
from pathlib import Path


def list_md_files(directory: Path) -> list[Path]:
    """Return sorted .md files from directory.

    Falls back to PowerShell enumeration on Windows where OneDrive reparse
    points cause Path.glob to silently return nothing.
    """
    files = list(directory.glob("*.md"))
    if not files and platform.system() == "Windows":
        try:
            result = subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    f'Get-ChildItem -LiteralPath "{directory}" -Filter "*.md" | '
                    f'Select-Object -ExpandProperty FullName',
                ],
                capture_output=True, text=True, timeout=60,
            )
            files = [Path(p.strip()) for p in result.stdout.splitlines() if p.strip()]
        except Exception:
            pass
    return sorted(files)
