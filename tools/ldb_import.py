#!/usr/bin/env python3
"""Fügt die Tageswerte eines Jahres (aus tools/ldb_auslesen.js) in data/historie-ldb.csv ein.

Aufruf:  python tools/ldb_import.py <jahr> <werte-datei> [pruefsumme]
  werte-datei: eine Zeile mit kommagetrennten cm-Werten, Reihenfolge 1. Januar bis 31. Dezember.
  pruefsumme:  sum((i+1)*wert) mit i ab 0 – wird vom Auslese-Skript ausgegeben.

Prüft: Anzahl der Werte == Tage des Jahres, alle Werte plausibel (0..600 cm).
Bestehende Tage werden überschrieben, andere Jahre bleiben unverändert.
"""
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "historie-ldb.csv"

if len(sys.argv) not in (3, 4):
    sys.exit(__doc__)
year = int(sys.argv[1])
vals = []
for tok in Path(sys.argv[2]).read_text(encoding="utf-8").strip().split(","):
    tok = tok.strip()
    if "*" in tok:                       # Lauflängen-Kodierung "wert*anzahl", z. B. 179*5
        w, n = tok.split("*")
        vals += [int(w)] * int(n)
    else:
        vals.append(int(float(tok)))
days = (date(year + 1, 1, 1) - date(year, 1, 1)).days
if len(vals) != days:
    sys.exit(f"Fehler: {len(vals)} Werte, erwartet {days} für {year}")
# Prüfsumme gegen Abtippfehler: sum((i+1)*wert), von tools/ldb_auslesen.js mitgeliefert (optional 3. Argument)
if len(sys.argv) == 4:
    check = sum((i + 1) * v for i, v in enumerate(vals))
    if check != int(sys.argv[3]):
        sys.exit(f"Fehler: Prüfsumme {check} != erwartet {sys.argv[3]} (Werte beim Übertragen verändert?)")
    print("Prüfsumme ok")
if not all(0 <= v <= 600 for v in vals):
    sys.exit("Fehler: unplausible Werte (außerhalb 0..600 cm)")

data = {}
if CSV_PATH.exists():
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        data = {r["datum"]: int(r["wasserstand_cm"]) for r in csv.DictReader(f)}
d0 = date(year, 1, 1)
for i, v in enumerate(vals):
    data[(d0 + timedelta(days=i)).isoformat()] = v
with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["datum", "wasserstand_cm"])
    for k in sorted(data):
        w.writerow([k, data[k]])
years = sorted({k[:4] for k in data})
print(f"{year}: {len(vals)} Tage eingefügt. Archiv: {len(data)} Tage, Jahre {years[0]}–{years[-1]} ({len(years)} Jahre)")
