#!/usr/bin/env python3
"""Holt die Regatten des SVH (Veranstalter N.062 SVH) von seglerinfo.de und schreibt data/regatten.json.

Aufruf:  python tools/seglerinfo_import.py [erstes_jahr] [letztes_jahr]     (Standard: 1996 bis laufendes Jahr)

Quelle: https://www.seglerinfo.de/regatten/Veranstaltungen.php?jahr=24&club_abk=SVH  (öffentliche Terminseite)
- Jede Zeile der Seite ist eine Regatta für EINE Klasse. Zeilen mit gleichem Namen und Zeitraum werden zu einer Regatta mit
  mehreren Klassen zusammengefasst.
- Abgesagte Klassen (Bemerkung "abgesagt"/"Absage ...") bleiben mit "abgesagt": true in der Datei; das Dashboard blendet sie aus.
- Nur Regatten auf dem Dümmer (Revier enthält "mmer") werden übernommen.
- Die Seite wird höflich abgefragt (kurze Pause zwischen den Jahren).
"""
import html
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

# Absagen, die auf seglerinfo.de nicht erkennbar sind (Bemerkungsspalte liefert dort oft nur einen Serverfehler): (Start, Namensteil)
MANUELL_ABGESAGT = {("2020-06-13", "haubentaucher"): "Corona"}
# Regatten, die auf seglerinfo.de fehlen, aber stattgefunden haben (werden beim Import wieder ergänzt)
MANUELL_ERGAENZT = [
    {"start": "2023-06-10", "end": "2023-06-11", "name": "Haubentaucher", "revier": "Dümmersee", "veranstalter": "N.062 SVH",
     "klassen": [{"klasse": "Klassen nicht erfasst", "bemerkung": "manuell ergänzt (fehlt auf seglerinfo.de)"}]},
]
OUT = Path(__file__).resolve().parents[1] / "data" / "regatten.json"
URL = "https://www.seglerinfo.de/regatten/Veranstaltungen.php?jahr={yy:02d}&klasse=&monat=&revier=&region=&dsvnr=&club_abk=SVH"


def fetch(year: int) -> str:
    req = urllib.request.Request(URL.format(yy=year % 100), headers={"User-Agent": "pegel-dashboard/1.0 (privates Projekt)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(cell: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cell))).replace("\xa0", " ").strip()


def parse(page: str, year: int):
    """Liefert Zeilen als dict; die Tabelle hat nicht geschlossene <td>-Tags, daher Aufteilung an '<td'."""
    rows = []
    for tr in re.split(r"<tr[^>]*>", page, flags=re.I)[1:]:
        cells = [clean(c) for c in re.split(r"<td[^>]*>", tr, flags=re.I)[1:]]
        if len(cells) < 8:
            continue
        dates = re.findall(r"(\d{2})\.(\d{2})\.(\d{4})", cells[0])
        if not dates:
            continue
        d0 = date(int(dates[0][2]), int(dates[0][1]), int(dates[0][0]))
        d1 = date(int(dates[-1][2]), int(dates[-1][1]), int(dates[-1][0]))
        faktor = None
        try:
            faktor = float(cells[6].replace(",", "."))
        except ValueError:
            pass
        rows.append({"start": d0.isoformat(), "end": d1.isoformat(), "name": cells[1], "klasse": cells[2], "revier": cells[3],
                     "veranstalter": cells[4], "status": cells[5], "faktor": faktor, "bemerkung": cells[7],
                     "ergebnisse": len(cells) > 8 and "haken" in tr.lower()})
    return rows


def group(rows):
    ev = {}
    for r in rows:
        key = (re.sub(r"[\s\-]+", " ", r["name"].lower()), r["start"], r["end"])        # "Dümmer-Finale" = "Dümmer Finale"
        e = ev.setdefault(key, {"name": r["name"], "start": r["start"], "end": r["end"], "revier": r["revier"],
                                "veranstalter": r["veranstalter"], "klassen": []})
        k = {"klasse": r["klasse"]}
        if r["status"]: k["status"] = r["status"]
        if r["faktor"] is not None: k["faktor"] = r["faktor"]
        if r["bemerkung"]: k["bemerkung"] = r["bemerkung"]
        if re.search(r"abgesagt|absage", r["bemerkung"], re.I): k["abgesagt"] = True
        for (st, nm), grund in MANUELL_ABGESAGT.items():
            if r["start"] == st and nm in r["name"].lower():
                k["abgesagt"] = True; k["bemerkung"] = f"{grund} (manuell ergänzt)"
        if r["ergebnisse"]: k["ergebnisse"] = True
        e["klassen"].append(k)
    return sorted(ev.values(), key=lambda e: (e["start"], e["name"]))


def main():
    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 1996
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else date.today().year
    alle, ohne_daemmer, jahre = [], 0, {}
    for y in range(y0, y1 + 1):
        try:
            rows = parse(fetch(y), y)
        except Exception as e:
            print(f"{y}: Fehler {e}", file=sys.stderr)
            continue
        rows = [r for r in rows if r["start"].startswith(str(y)) or r["end"].startswith(str(y))]
        dm = [r for r in rows if "mmer" in r["revier"]]
        ohne_daemmer += len(rows) - len(dm)
        evs = group(dm)
        jahre[y] = (len(rows), len(evs))
        alle += evs
        print(f"{y}: {len(rows):3d} Zeilen -> {len(evs):2d} Regatten", flush=True)
        time.sleep(0.6)
    for ex in MANUELL_ERGAENZT:
        if not any(e["start"] == ex["start"] and ex["name"].lower() in e["name"].lower() for e in alle):
            alle.append(dict(ex))
    alle.sort(key=lambda e: (e["start"], e["name"]))
    data = {"quelle": f"seglerinfo.de – Termine, Meldeadressen, Ergebnisse (Veranstalter N.062 SVH), abgerufen am "
                      f"{datetime.now().strftime('%d.%m.%Y')} für {y0}–{y1}",
            "regatten": alle}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    gesamt = len(alle)
    abg = sum(1 for e in alle if all(k.get("abgesagt") for k in e["klassen"]))
    print(f"\n{gesamt} Regatten in {OUT.name} (davon {abg} komplett abgesagt, {ohne_daemmer} Zeilen anderer Reviere übersprungen)")


if __name__ == "__main__":
    main()
