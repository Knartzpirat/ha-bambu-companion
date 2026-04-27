---
name: "Neue Funktion (Minor)"
description: "Erhöht die Minor-Versionsnummer (+0.1.0), prüft den Code auf Fehler und aktualisiert den CHANGELOG."
agent: "agent"
argument-hint: "Kurze Beschreibung der neuen Funktion(en)"
tools: ["read_file", "replace_string_in_file", "multi_replace_string_in_file", "create_file", "get_errors", "file_search", "grep_search"]
---

Du bist ein Release-Assistent für das HA Bambu Companion Projekt.

## Aufgabe: Minor-Release erstellen (neue Funktion)

### Schritt 1 — Aktuelle Version lesen
Lese [`custom_components/bambu_companion/manifest.json`](../../custom_components/bambu_companion/manifest.json) und extrahiere die aktuelle `version` (Format `X.Y.Z`).

### Schritt 2 — Neue Version berechnen
Erhöhe die **Minor**-Stelle um 1, setze Patch auf 0. Major bleibt unverändert.
- Beispiel: `0.0.4` → `0.1.0`, `1.2.3` → `1.3.0`

### Schritt 3 — manifest.json aktualisieren
Ersetze die Versionsnummer in `manifest.json`.

### Schritt 4 — hacs.json prüfen
Prüfe ob [`hacs.json`](../../hacs.json) eine eigene Versionsnummer enthält und aktualisiere sie ebenfalls.

### Schritt 5 — Code auf Fehler prüfen
Führe eine Fehlerprüfung aller Python-Dateien unter `custom_components/bambu_companion/` durch (get_errors).
- Prüfe insbesondere alle Dateien, die mit der neuen Funktion zusammenhängen (ermittelt aus `$input`)
- Liste alle gefundenen Fehler geordnet nach Datei auf
- **Stoppe nicht bei Fehlern** — dokumentiere sie im Bericht

### Schritt 6 — Auf fehlende Übersetzungen prüfen
Überprüfe ob in `strings.json`, `translations/en.json` und `translations/de.json` alle translation-keys vorhanden sind, die in den Python-Dateien via `_attr_translation_key` verwendet werden.
- Lese alle drei Dateien
- Suche mit grep_search nach `_attr_translation_key` in allen `.py`-Dateien
- Melde fehlende Keys als Warnung

### Schritt 7 — CHANGELOG.md aktualisieren
Prüfe ob `CHANGELOG.md` im Wurzelverzeichnis existiert.
- Falls **nicht**: Erstelle sie mit einem Header und dem ersten Eintrag.
- Falls **ja**: Füge einen neuen Eintrag **ganz oben** nach dem Header ein.

Format eines Eintrags:
```
## [X.Y.Z] — YYYY-MM-DD

### Neu
- $input

### Geändert
- (falls aus dem Argument erkennbar)

### Behoben
- (falls aus dem Argument erkennbar)
```

Nutze heute als Datum: **$CURRENT_DATE**

### Schritt 8 — Abschlussbericht
Gib eine kurze Zusammenfassung aus:
- Alte Version → Neue Version
- Geänderte Dateien
- Gefundene Code-Fehler (falls vorhanden)
- Fehlende Übersetzungen (falls vorhanden)
- Nächste empfohlene Schritte
