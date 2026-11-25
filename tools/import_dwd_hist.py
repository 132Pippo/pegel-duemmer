#!/usr/bin/env python3
"""Einmaliger Import der DWD-Historie (Diepholz, 1952 bis Ende Vorjahr) ins Niederschlagsarchiv.

Aufruf:  python tools/import_dwd_hist.py <tageswerte_RR_00963_..._hist.zip>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dwd  # noqa: E402

if len(sys.argv) != 2:
    sys.exit(__doc__)
new = dwd.parse_zip(Path(sys.argv[1]).read_bytes())
added, total = dwd.merge(new)
print(f"{len(new)} Tage gelesen ({min(new)} bis {max(new)}), {added} neu, Archiv: {total} Tage")
