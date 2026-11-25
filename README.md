# Pegel Dümmer-Ost

Dashboard für den Wasserstand des Dümmers (NLWKN-Pegel Dümmer-Ost) mit Soll-Linie, Regen, Verdunstung, Jahresvergleich,
Regatten und Regatta-Vergleich. Eine einzige Seite (`index.html`), die Daten liegen als CSV/JSON in `data/`.

## Lokal starten

- `Dashboard-starten.bat` doppelklicken (holt neue Werte und öffnet die Seite), oder
- `python fetch.py` und danach `python -m http.server 8000` im Ordner, dann http://localhost:8000 öffnen.

Der NLWKN-Schlüssel steht lokal in `secret.json` (`{"subscription_key": "..."}`). Die Datei steht in `.gitignore` und wird nie veröffentlicht.

## Online stellen (GitHub Pages)

1. Auf github.com ein **öffentliches** Repository anlegen (z. B. `pegel-duemmer`), leer, ohne README.
2. Im Projektordner:
   ```
   git init -b main
   git add .
   git commit -m "Pegel-Dashboard"
   git remote add origin https://github.com/DEINNAME/pegel-duemmer.git
   git push -u origin main
   ```
3. Im Repository **Settings > Secrets and variables > Actions > New repository secret**:
   Name `NLWKN_KEY`, Wert = der Schlüssel aus `secret.json`.
4. **Settings > Pages > Build and deployment > Source: GitHub Actions** wählen.
5. Reiter **Actions > "Daten aktualisieren und Seite veröffentlichen" > Run workflow**. Nach etwa einer Minute steht die Adresse
   (`https://DEINNAME.github.io/pegel-duemmer/`) im Lauf unter "deploy".

Danach läuft die Aktualisierung alle 3 Stunden von selbst und speichert das Archiv im Repository.
Hinweis: GitHub schaltet geplante Läufe in öffentlichen Repositories ab, wenn 60 Tage lang nichts im Repository passiert;
dann einmal im Reiter Actions wieder aktivieren.

## Regatten

- Vergangene Regatten (SVH, SCC): `python tools/seglerinfo_import.py` (seglerinfo.de, einmalig/bei Bedarf).
- Kommende Regatten: `manage2sail.py` (Vereinsseiten bei manage2sail.com), läuft bei jedem `fetch.py`. Es ersetzt bei jedem Lauf alle Einträge ab heute.
- Manuelle Korrekturen (Absagen, falsche oder fehlende Termine) stehen oben in `tools/seglerinfo_import.py`.

## Datenquellen

NLWKN Pegelonline und Landesdatenbank (Wasserstand), DWD Station Diepholz (Niederschlag), Open-Meteo (Verdunstung, Vorhersage),
seglerinfo.de (vergangene Regatten), manage2sail.com (kommende Regatten). Bei einer öffentlichen Seite die Nutzungsbedingungen dieser Quellen beachten.
