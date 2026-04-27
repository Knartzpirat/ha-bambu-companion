---
name: "Neue Version (Major)"
description: "Erhöht die Major-Versionsnummer (+1.0.0), aktualisiert README und CHANGELOG, prüft den Code auf Fehler."
agent: "agent"
argument-hint: "Kurze Beschreibung der Breaking Changes / was sich geändert hat"
tools: ["read_file", "replace_string_in_file", "multi_replace_string_in_file", "create_file", "get_errors", "file_search", "grep_search"]
---

Du bist ein Release-Assistent für das HA Bambu Companion Projekt.

## Aufgabe: Major-Release erstellen

### Schritt 1 — Aktuelle Version lesen
Lese [`custom_components/bambu_companion/manifest.json`](../../custom_components/bambu_companion/manifest.json) und extrahiere die aktuelle `version` (Format `X.Y.Z`).

### Schritt 2 — Neue Version berechnen
Erhöhe die **Major**-Stelle um 1, setze Minor und Patch auf 0.
- Beispiel: `0.0.4` → `1.0.0`

### Schritt 3 — manifest.json aktualisieren
Ersetze die Versionsnummer in `manifest.json`.

### Schritt 4 — hacs.json prüfen
Prüfe ob [`hacs.json`](../../hacs.json) eine eigene Versionsnummer enthält und aktualisiere sie ebenfalls.

### Schritt 5 — Code auf Fehler prüfen
Führe eine Fehlerprüfung aller Python-Dateien unter `custom_components/bambu_companion/` durch (get_errors). Liste alle gefundenen Fehler auf. **Stoppe nicht bei Fehlern** — dokumentiere sie im Release-Bericht, bevor du weitermachst.

### Schritt 6 — README.md aktualisieren
Lese [`README.md`](../../README.md) und aktualisiere:
- Versionsnummern, die explizit genannt werden (z. B. in Badges oder Installationsanweisungen)
- Den Abschnitt "What's New" oder "Features", falls vorhanden — ergänze die neuen Features aus dem Argument `$input`

### Schritt 7 — CHANGELOG.md aktualisieren
Prüfe ob `CHANGELOG.md` im Wurzelverzeichnis existiert.
- Falls **nicht**: Erstelle sie mit einem Header und dem ersten Eintrag.
- Falls **ja**: Füge einen neuen Eintrag **ganz oben** nach dem Header ein.

Format eines Eintrags:
```
## [X.Y.Z] — YYYY-MM-DD

### Breaking Changes
- $input (oder "Keine" wenn leer)

### Neu
- (aus dem Argument beschrieben)

### Geändert
- (aus dem Argument beschrieben)

### Behoben
- (aus dem Argument beschrieben)
```

Nutze heute als Datum: **$CURRENT_DATE**

### Schritt 8 — Abschlussbericht
Gib eine kurze Zusammenfassung aus:
- Alte Version → Neue Version
- Geänderte Dateien
- Gefundene Code-Fehler (falls vorhanden)
- Nächste empfohlene Schritte (z. B. git tag, HACS-Release)
