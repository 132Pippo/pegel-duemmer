#!/usr/bin/env python3
"""Holt die letzten 30 Tage Wasserstand (Dümmer-Ost) vom NLWKN und
hängt neue Messwerte an das dauerhafte CSV-Archiv an.

Aufruf:  python fetch.py
Ein Lauf alle paar Tage genügt, da sich die 30-Tage-Fenster überlappen.
Der Subscription-Key kann alternativ per Umgebungsvariable NLWKN_KEY gesetzt werden.
"""
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
def _load_key():
    """Schlüssel aus der Umgebungsvariable NLWKN_KEY (GitHub-Secret) oder aus secret.json (nur lokal, nicht im Repository)."""
    key = os.environ.get("NLWKN_KEY")
    secret = BASE / "secret.json"
    if not key and secret.exists():
        key = json.loads(secret.read_text(encoding="utf-8")).get("subscription_key")
    if not key:
        raise SystemExit("Kein NLWKN-Schlüssel: Umgebungsvariable NLWKN_KEY setzen oder secret.json anlegen (siehe README.md).")
    return key


KEY = _load_key()
CSV_PATH = BASE / CFG["csv_path"]
HEADER = ["timestamp_utc", "wasserstand_cm"]


def fetch_series():
    url = (
        f"{CFG['api_base']}chart/station/{CFG['station_id']}"
        f"/datenspuren/parameter/{CFG['parameter_id']}"
        f"/tage/-{CFG['days']}/forecast/false?subscription-key={KEY}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "pegel-archiv/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    spuren = data["getPegelDatenspurenChartResult"]
    if not spuren or not spuren[0].get("Pegelstaende"):
        raise RuntimeError("API lieferte keine Pegelstaende")
    out = {}
    for p in spuren[0]["Pegelstaende"]:
        ms = int(p["DatumUTC"].split("(")[1].split(")")[0].split("+")[0])
        ts = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        out[ts.strftime("%Y-%m-%dT%H:%M:%SZ")] = p["Wert"]
    return out


def load_archive():
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return {row["timestamp_utc"]: row["wasserstand_cm"] for row in csv.DictReader(f)}


def main():
    new = fetch_series()
    archive = load_archive()
    added = sum(1 for k in new if k not in archive)
    archive.update({k: v for k, v in new.items()})
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CSV_PATH.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        for k in sorted(archive):
            w.writerow([k, archive[k]])
    tmp.replace(CSV_PATH)
    print(f"{len(new)} Werte geladen, {added} neu, Archiv: {len(archive)} Zeilen "
          f"({min(archive)} bis {max(archive)})")


if __name__ == "__main__":
    rc = 0
    try:
        main()
    except Exception as e:
        print(f"Fehler (Pegel): {e}", file=sys.stderr)
        rc = 1
    # Niederschlag (DWD Diepholz) unabhängig vom Pegelabruf – ein Fehler hier stoppt nichts
    try:
        import dwd
        print(dwd.update_recent())
    except Exception as e:
        print(f"Hinweis: Niederschlag nicht aktualisiert ({e})", file=sys.stderr)
    # Verdunstung (Open-Meteo ET0 × 1,08), ebenfalls unabhängig
    try:
        import verdunstung
        print(verdunstung.update())
    except Exception as e:
        print(f"Hinweis: Verdunstung nicht aktualisiert ({e})", file=sys.stderr)
    # Kommende Regatten (SVH, SCC) von manage2sail.com – ebenfalls unabhängig
    try:
        import manage2sail
        print(manage2sail.update())
    except Exception as e:
        print(f"Hinweis: kommende Regatten nicht aktualisiert ({e})", file=sys.stderr)
    sys.exit(rc)
