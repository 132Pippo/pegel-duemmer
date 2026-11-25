"""Tagesniederschlag der DWD-Station Diepholz (Nr. 00963, ca. 6 km vom Dümmer).

Quelle: DWD Climate Data Center, daily/more_precip (Open Data).
  historical: tageswerte_RR_00963_19520901_20251231_hist.zip  (einmalig, tools/import_dwd_hist.py)
  recent:     tageswerte_RR_00963_akt.zip                      (wird von fetch.py bei jedem Lauf aktualisiert)

Die Tageswerte (RS, mm) gelten für 06:00 UTC bis 06:00 UTC des Folgetags (ab 04/2001; davor 07:30 bis 07:30),
sind also nicht auf Mitternacht ausgerichtet. Fehlwerte (-999) werden nicht gespeichert.
"""
import csv
import io
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
CSV_PATH = BASE / "data" / "niederschlag.csv"
RECENT_URL = ("https://opendata.dwd.de/climate_environment/CDC/observations_germany/"
              "climate/daily/more_precip/recent/tageswerte_RR_00963_akt.zip")
HEADER = ["datum", "niederschlag_mm"]


def parse_zip(data: bytes) -> dict:
    """Liest die Produktdatei 'produkt_nieder_tag_*' aus dem ZIP -> {YYYY-MM-DD: mm}."""
    z = zipfile.ZipFile(io.BytesIO(data))
    name = next(n for n in z.namelist() if n.startswith("produkt_nieder_tag"))
    out = {}
    lines = z.read(name).decode("latin-1").splitlines()
    cols = [c.strip() for c in lines[0].split(";")]
    i_date, i_rs = cols.index("MESS_DATUM"), cols.index("RS")
    for line in lines[1:]:
        f = [c.strip() for c in line.split(";")]
        if len(f) <= i_rs or not f[i_date].isdigit():
            continue
        mm = float(f[i_rs])
        if mm <= -998:                       # -999 = Fehlwert
            continue
        d = datetime.strptime(f[i_date], "%Y%m%d").strftime("%Y-%m-%d")
        out[d] = mm
    return out


def load_archive() -> dict:
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return {r["datum"]: float(r["niederschlag_mm"]) for r in csv.DictReader(f)}


def merge(new: dict) -> tuple[int, int]:
    """Fügt neue Werte hinzu (neue überschreiben alte). Gibt (neu, gesamt) zurück."""
    archive = load_archive()
    added = sum(1 for k in new if k not in archive)
    archive.update(new)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CSV_PATH.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        for k in sorted(archive):
            w.writerow([k, f"{archive[k]:.1f}"])
    tmp.replace(CSV_PATH)
    return added, len(archive)


def update_recent() -> str:
    req = urllib.request.Request(RECENT_URL, headers={"User-Agent": "pegel-archiv/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        new = parse_zip(r.read())
    added, total = merge(new)
    return f"Niederschlag (DWD Diepholz): {len(new)} Tage geladen, {added} neu, Archiv: {total} Tage"
