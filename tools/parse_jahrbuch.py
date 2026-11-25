#!/usr/bin/env python3
"""Liest die Tageswerte (cm) des Pegels Dümmer-Ost aus einem NLWKN-Jahrbuch
(Deutsches Gewässerkundliches Jahrbuch, Weser-/Emsgebiet) und prüft sie gegen
die Monatswerte NW/MW/HW der Tabelle.

Aufruf:  python tools/parse_jahrbuch.py <pdf> <jahr> [ausgabe.csv]
Beispiel: python tools/parse_jahrbuch.py dgj1999.pdf 1999 data/historie-tageswerte.csv

Das Skript hängt an die Ausgabe-CSV an (Deduplizierung über das Datum).
Getestet nur mit dem Jahrbuch 1999; andere Jahrgänge können anders aufgebaut sein.
"""
import calendar
import csv
import re
import sys
from pathlib import Path

import pypdf

STATION = "4961130"


def find_page(reader):
    for i, p in enumerate(reader.pages):
        t = p.extract_text() or ""
        if STATION in t and "Tageswerte" in t and "Wasserst" in t:
            return p
    raise RuntimeError("Seite mit Pegel Dümmer-Ost nicht gefunden")


def fragments(page):
    items = []

    def visit(text, cm, tm, fd, fs):
        if text.strip():
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            items.append((round(x, 1), round(y, 1), text.strip()))

    page.extract_text(visitor_text=visit)
    return items


def parse(pdf, year):
    page = find_page(pypdf.PdfReader(pdf))
    items = fragments(page)
    # Tageszeilen: Zeilenhöhe y der Tagesbeschriftung "1." .. "31."
    day_y = {}
    for x, y, t in items:
        m = re.fullmatch(r"(\d{1,2})\.", t)
        if m and 80 < x < 95 and y > 500:
            day_y[int(m.group(1))] = y
    if sorted(day_y) != list(range(1, 32)):
        raise RuntimeError(f"Tagesbeschriftungen unvollständig: {sorted(day_y)}")

    def row_at(y, tol=0.6):
        for xx, yy, t in items:
            if abs(yy - y) < tol and 100 < xx < 160 and re.fullmatch(r"[\d\s]+", t):
                return [int(v) for v in t.split()]
        return None

    # 14 Spalten: Nov(Vorjahr), Dez(Vorjahr), Jan..Dez
    cols = [(year - 1, 11), (year - 1, 12)] + [(year, m) for m in range(1, 13)]
    data = {}
    for day in range(1, 32):
        vals = row_at(day_y[day])
        if vals is None:
            raise RuntimeError(f"Tag {day}: keine Werte gefunden")
        valid = [c for c in cols if day <= calendar.monthrange(*c)[1]]
        if len(vals) != len(valid):
            raise RuntimeError(f"Tag {day}: {len(vals)} Werte, erwartet {len(valid)}")
        for (yy, mm), v in zip(valid, vals):
            data[f"{yy:04d}-{mm:02d}-{day:02d}"] = v

    # Monatsstatistik (NW, MW, HW) – Zeilen unterhalb der Tagestabelle
    # y wächst nach oben: höchster y-Wert = erste Zeile = NW, dann MW, dann HW
    stat_rows = sorted(
        ((y, [int(v) for v in t.split()])
         for x, y, t in items
         if 100 < x < 160 and 485 < y < 515 and re.fullmatch(r"[\d\s]+", t)
         and len(t.split()) == 14),
        reverse=True,
    )
    if len(stat_rows) != 3:
        raise RuntimeError(f"Monatsstatistik nicht gefunden ({len(stat_rows)} Zeilen)")
    nw, mw, hw = (r for _, r in stat_rows)
    problems = []
    for i, (yy, mm) in enumerate(cols):
        vs = [v for d, v in data.items() if d.startswith(f"{yy:04d}-{mm:02d}")]
        mean = sum(vs) / len(vs)
        # NW/HW sind Extremwerte (Momentanwerte), die Tabelle enthält Tagesmittel:
        # NW <= Tagesminimum und HW >= Tagesmaximum, beides nur wenig daneben.
        if not (nw[i] <= min(vs) <= nw[i] + 3):
            problems.append(f"{yy}-{mm:02d}: Tagesmin {min(vs)} passt nicht zu NW {nw[i]}")
        if not (hw[i] - 8 <= max(vs) <= hw[i]):
            problems.append(f"{yy}-{mm:02d}: Tagesmax {max(vs)} passt nicht zu HW {hw[i]}")
        if abs(mean - mw[i]) > 1.0:
            problems.append(f"{yy}-{mm:02d}: Mittel {mean:.1f} != MW {mw[i]}")
    return data, problems


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    pdf, year = sys.argv[1], int(sys.argv[2])
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    data, problems = parse(pdf, year)
    print(f"{len(data)} Tageswerte ({min(data)} bis {max(data)})")
    if problems:
        print("ABWEICHUNGEN zur Monatsstatistik:")
        for p in problems:
            print("  ", p)
        sys.exit(2)
    print("Prüfung gegen NW/MW/HW aller 14 Monate: ok")
    if out:
        existing = {}
        if out.exists():
            with out.open(newline="", encoding="utf-8") as f:
                existing = {r["datum"]: r["wasserstand_cm"] for r in csv.DictReader(f)}
        existing.update({k: str(v) for k, v in data.items()})
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["datum", "wasserstand_cm"])
            for k in sorted(existing):
                w.writerow([k, existing[k]])
        print(f"Geschrieben: {out} ({len(existing)} Zeilen)")


if __name__ == "__main__":
    main()
