"""Geschätzte Verdunstung der Wasserfläche des Dümmers (Tageswerte, mm).

Verfahren: FAO-Gras-Referenzverdunstung ET0 von Open-Meteo (Archiv, Rasterdaten am Dümmer) × 1,08.
Der Faktor 1,08 ist an das NLWKN-Gutachten Wolter & Köhler (2012) geeicht: dort Verdunstung der freien
Wasserfläche (Penman mit Wassertemperatur, DVWK 238, Station Diepholz) im Mittel 2,02 mm/Tag für 1979–09/2012;
Open-Meteo-ET0 im selben Zeitraum 1,87 mm/Tag.  -> 2,02 / 1,87 ≈ 1,08

Datei: data/verdunstung.csv  (datum, et0_mm, see_mm)
Die Uferzone (Schilf) ist nicht enthalten.
"""
import csv
import json
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
CSV_PATH = BASE / "data" / "verdunstung.csv"
FAKTOR = 1.08
LAT, LON = 52.53, 8.35
URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
       "&start_date={s}&end_date={e}&daily=et0_fao_evapotranspiration&timezone=Europe%2FBerlin")


def fetch(start: str, end: str) -> dict:
    url = URL.format(lat=LAT, lon=LON, s=start, e=end)
    req = urllib.request.Request(url, headers={"User-Agent": "pegel-archiv/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)["daily"]
    # Die jüngsten Tage fehlen im Archiv oft noch (None) – die werden übersprungen
    return {t: v for t, v in zip(d["time"], d["et0_fao_evapotranspiration"]) if v is not None}


def load() -> dict:
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return {r["datum"]: float(r["et0_mm"]) for r in csv.DictReader(f)}


def write(data: dict):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CSV_PATH.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["datum", "et0_mm", "see_mm"])
        for k in sorted(data):
            w.writerow([k, f"{data[k]:.2f}", f"{data[k] * FAKTOR:.2f}"])
    tmp.replace(CSV_PATH)


def update(start: str | None = None) -> str:
    data = load()
    if start is None:
        # Erstbefüllung ab 1998, sonst die letzten 14 Tage neu holen (Archiv wird nachträglich vervollständigt)
        start = "1998-01-01" if not data else (date.fromisoformat(max(data)) - timedelta(days=14)).isoformat()
    end = (date.today() - timedelta(days=1)).isoformat()
    new = fetch(start, end)
    added = sum(1 for k in new if k not in data)
    data.update(new)
    write(data)
    return f"Verdunstung (Open-Meteo ET0 × {FAKTOR}): {len(new)} Tage geladen, {added} neu, Archiv: {len(data)} Tage bis {max(data)}"


if __name__ == "__main__":
    print(update())
