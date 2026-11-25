#!/usr/bin/env python3
"""Kommende Regatten auf dem Dümmer von manage2sail.com -> data/regatten.json.

Quelle: die Vereinsseiten der Seglervereinigung Hüde (SVH) und des Segler-Club Clarholz (SCC) auf manage2sail.com
(öffentliche Seiten, je Verein eine Tabelle "Veranstaltungen" mit Datum und Name; Jahr per ?year=JJJJ).

Regel: Vergangene Regatten kommen aus seglerinfo.de (tools/seglerinfo_import.py), kommende (Ende heute oder später) von hier.
Bei jedem Lauf werden die bisherigen manage2sail-Einträge ersetzt und kommende seglerinfo-Einträge entfernt, sobald der Abruf
geklappt hat. Trainings und Saisonkurse werden übersprungen.

Aufruf:  python manage2sail.py            (aktualisiert data/regatten.json)
         python manage2sail.py --zeigen   (nur anzeigen, was die Seiten liefern, auch Vergangenes; schreibt nichts)
Wird auch von fetch.py aufgerufen.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent / "data" / "regatten.json"
BASE = "https://manage2sail.com/de-DE/Club/Detail/{id}"
CLUBS = {
    "SVH": ("19a00d59-91bf-4ab2-b912-2424de6c2110", "N.062 SVH"),    # Seglervereinigung Hüde e. V. Dümmer
    "SCC": ("dfa9d47c-c00a-42b3-b9e2-f54aa8650081", "N.176 SCC"),    # Segler-Club Clarholz e.V.
}
TODAY = date.today()                              # für Tests überschreibbar
SKIP = re.compile(r"training|saisonkurs|lehrgang|trainingslager", re.I)
ROW = re.compile(r'<td[^>]*>\s*(\d{4})\s*</td>\s*<td[^>]*>\s*([^<]*?)\s*</td>\s*<td[^>]*>\s*<a href="(/[^"]*event/[^"]+)"[^>]*>(.*?)</a>', re.S)


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "pegel-dashboard/1.0 (privates Projekt)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def _dates(year: int, text: str):
    """'11.04 - 12.04' oder '22.08' -> (start, ende) als ISO-Strings."""
    tag = re.findall(r"(\d{1,2})\.(\d{1,2})\.?", text)
    if not tag:
        return None
    d0 = date(year, int(tag[0][1]), int(tag[0][0]))
    d1 = date(year, int(tag[-1][1]), int(tag[-1][0]))
    if d1 < d0:                                   # über den Jahreswechsel
        d1 = date(year + 1, d1.month, d1.day)
    return d0.isoformat(), d1.isoformat()


def club_events(club: str, jahre=None):
    """Alle Veranstaltungen eines Vereins für die gewünschten Jahre (Standard: aktuelles Jahr und später)."""
    cid, veranstalter = CLUBS[club]
    first = _get(BASE.format(id=cid))
    verfuegbar = sorted({int(y) for y in re.findall(r'<option value="(\d{4})"', first)})
    heute = TODAY.year
    wanted = verfuegbar if jahre == "alle" else [y for y in verfuegbar if y >= heute]
    pages = {}
    for y in wanted:
        pages[y] = _get(BASE.format(id=cid) + f"?year={y}")
    if not wanted:                                # noch keine Veranstaltungen für dieses oder spätere Jahre
        pages[heute] = first
    out = []
    for y, page in pages.items():
        for yy, dtxt, link, name in ROW.findall(page):
            if int(yy) != y:
                continue
            ds = _dates(int(yy), _clean(dtxt))
            nm = re.sub(r"\s+20\d\d$", "", _clean(name))
            if not ds or not nm:
                continue
            out.append({"start": ds[0], "end": ds[1], "name": nm, "revier": "Dümmersee", "veranstalter": veranstalter,
                        "klassen": [{"klasse": "Klassen siehe manage2sail"}], "quelle": "manage2sail",
                        "url": "https://manage2sail.com" + link})
    return out


def update(zeigen: bool = False) -> str:
    heute = TODAY.isoformat()
    neu, fehler = [], []
    for club in CLUBS:
        try:
            neu += club_events(club, "alle" if zeigen else None)
        except Exception as e:                    # ein ausgefallener Verein stoppt nichts
            fehler.append(f"{club}: {e}")
    if zeigen:
        for e in sorted(neu, key=lambda e: e["start"]):
            print(e["start"], e["end"], "|", e["name"], "|", e["veranstalter"], "| übersprungen" if SKIP.search(e["name"]) else "")
        return f"{len(neu)} Einträge gelesen" + (f", Fehler: {fehler}" if fehler else "")
    if fehler:
        return "manage2sail nicht aktualisiert (" + "; ".join(fehler) + ")"
    neu = [e for e in neu if e["end"] >= heute and not SKIP.search(e["name"])]
    d = json.loads(OUT.read_text(encoding="utf-8"))
    alt = d["regatten"]
    behalten = [r for r in alt if r.get("quelle") != "manage2sail" and r["end"] < heute]      # Vergangenes bleibt aus seglerinfo
    alle = sorted(behalten + neu, key=lambda e: (e["start"], e["name"]))
    d["regatten"] = alle
    d["quelle_kommend"] = f"manage2sail.com (Vereinsseiten SVH und SCC), abgerufen am {datetime.now().strftime('%d.%m.%Y')}"
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"manage2sail: {len(neu)} kommende Regatten, Datei hat {len(alle)} Einträge"


if __name__ == "__main__":
    print(update(zeigen="--zeigen" in sys.argv))
