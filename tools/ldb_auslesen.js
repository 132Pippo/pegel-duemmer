/* Liest die Tageswerte (Wasserstand Tagesmittelwert, cm) von Dümmer-Ost aus der NLWKN-Landesdatenbank
   (www.wasserdaten.niedersachsen.de) – ein Messjahr pro Durchlauf.

   Vorgehen:
   1. In der Landesdatenbank die Messstelle Dümmer-Ost (4961130) öffnen und das Fenster
      "Wasserstände und Abflüsse - Messwerte" aufrufen. Messjahr (genau ein Jahr!) und
      Parameter "Wasserstand Tagesmittelwert" wählen, bis die Tabelle erscheint.
   2. Dieses Skript in der Browser-Konsole der Seite ausführen. Es scrollt die Tabelle durch
      (sie lädt in Blöcken von 60 Zeilen nach) und liefert {datum -> Wert}.
   3. Die Werte nach data/historie-ldb.csv übernehmen (Spalten: datum,wasserstand_cm).

   Stand: für 2024 getestet (366 Tage, lückenlos). Die Oberfläche kann sich ändern. */
(async () => {
  const frame = () => [...document.querySelectorAll('iframe')].find(x => {
    try { return x.contentDocument.getElementById('richResultTable:b'); } catch (e) { return false; }
  });
  const b = frame().contentDocument.getElementById('richResultTable:b');
  const got = new Map(); let stable = 0, last = -1;
  b.scrollTop = 0; await new Promise(r => setTimeout(r, 500));
  for (let i = 0; i < 80 && stable < 4; i++) {
    const re = /(\d{2}\.\d{2}\.\d{4})\s+Wasserstand Tagesmittelwert\s+(-?[\d.]+,\d+)/g; let m; const txt = b.innerText;
    while ((m = re.exec(txt))) got.set(m[1], m[2]);
    stable = got.size === last ? stable + 1 : 0; last = got.size;
    b.scrollTop = b.scrollTop + b.clientHeight * 0.9;
    if (b.scrollTop + b.clientHeight >= b.scrollHeight - 5) b.scrollTop = b.scrollHeight;
    await new Promise(r => setTimeout(r, 450));
  }
  return got;
})();
