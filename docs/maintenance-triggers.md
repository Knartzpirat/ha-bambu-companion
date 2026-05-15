# Wartungsplan – Trigger-Übersicht

Diese Seite erklärt, **wann und wie** jede Wartungsaufgabe ihren Zähler erhöht, welche Bedingungen gelten und wie zurückgesetzt wird.

---

## Trigger-Typen

| Trigger | Beschreibung | Bedingung für Zähler-Inkrement |
|---|---|---|
| `print_hours` | Stunden im Druckbetrieb | Druckstatus = `printing` (jede Aktualisierung = +Δt h) |
| `nozzle_hours` | Düsen-Betriebsstunden (Einzeldüse) | Druckstatus = `printing` **UND** Düsentemperatur > 100 °C |
| `left_nozzle_hours` | Stunden linke Düse (H2D) | Druckstatus = `printing` **UND** linke Düsentemperatur > 100 °C |
| `right_nozzle_hours` | Stunden rechte Düse (H2D) | Druckstatus = `printing` **UND** rechte Düsentemperatur > 100 °C |
| `total_hours` | Gesamte Maschinenlaufzeit | Bezieht sich auf `ha-bambulab`-Sensor `total_usage_hours` (absoluter Wert, kein Inkrement). Wenn dieser Sensor nicht verfügbar ist, wird intern `print_hours` als Fallback verwendet. |
| `print_count` | Anzahl erfolgreicher Drucke | +1 pro erfolgreich abgeschlossenem Druck |
| `laser_hours` | Laser-Betriebsstunden (H2D) | `tool_module_state` = `laser` (jede Aktualisierung = +Δt h) |
| `laser_jobs` | Anzahl abgeschlossener Laserjobs (H2D) | Übergang: war `laser` → ist nicht mehr `laser` (= Job beendet) |

> **Aktualisierungsintervall**: Der Koordinator aktualisiert alle 60 Sekunden. Jeder Durchlauf fügt ~0,0167 h (1 Minute) zu Stundenzählern hinzu, wenn die Bedingung zutrifft.

---

## Alle Wartungsaufgaben

### 🔩 Druckkopf / Düse

| Aufgabe | Trigger | Standard | Gilt für | Besonderheit |
|---|---|---|---|---|
| Düse reinigen | `nozzle_hours` | 200 h | Alle Modelle | Nur Einzeldüse (`single_nozzle_only`) |
| Düse gewechselt *(Stundenzähler reset)* | `nozzle_hours` | 800 h | Alle Modelle | `reset_counter`: setzt `nozzle_hours` auf 0; setzt auch Baseline von „Düse reinigen" zurück |
| Linke Düse reinigen | `left_nozzle_hours` | 200 h | H2D | Nur Dualdüse |
| Linke Düse gewechselt | `left_nozzle_hours` | 800 h | H2D | `reset_counter`: setzt `left_nozzle_hours` auf 0; setzt auch „Linke Düse reinigen" zurück |
| Rechte Düse reinigen | `right_nozzle_hours` | 200 h | H2D | Nur Dualdüse |
| Rechte Düse gewechselt | `right_nozzle_hours` | 800 h | H2D | `reset_counter`: setzt `right_nozzle_hours` auf 0; setzt auch „Rechte Düse reinigen" zurück |
| Schneidmesser prüfen / wechseln | `print_count` | 250 Drucke | Alle Modelle | ca. 5.000–7.000 Schnitte bis Verschleiß |
| PTFE-Tube prüfen / wechseln | `print_hours` | 500 h | Alle Modelle | — |
| Hotend / Heatbreak reinigen | `print_hours` | 500 h | Alle Modelle | — |
| Extruder-Zahnrad reinigen | `print_hours` | 300 h | Alle Modelle | — |
| Druckkopf-Kabel prüfen | `print_hours` | 1.000 h | Alle Modelle | — |

### ⚙️ Mechanik / Antrieb

| Aufgabe | Trigger | Standard | Gilt für | Hinweis |
|---|---|---|---|---|
| Y/Z-Linearschienen reinigen & konservieren | `print_hours` | 300 h | Alle Modelle | Bambu Wiki: monatlich prüfen, alle 3 Monate Korrosionsschutz |
| Z-Gewindespindeln schmieren | `print_hours` | 500 h | Alle Modelle | Bambu Wiki: alle 3 Monate |
| Carbon-Stangen reinigen *(IPA, kein Öl!)* | `print_hours` | 200 h | X1, X1C, X1E, P1P, P1S | Bambu Wiki: alle 5 Rollen ABS/ASA oder monatlich |
| Riemenspannung prüfen (X & Y) | `print_hours` | 500 h | Alle Modelle | — |

### 🛏️ Druckbett

| Aufgabe | Trigger | Standard | Gilt für |
|---|---|---|---|
| Druckbett reinigen | `print_count` | 20 Drucke | Alle Modelle |

### 💨 Lüfter & Filter

| Aufgabe | Trigger | Standard | Gilt für | Hinweis |
|---|---|---|---|---|
| Alle Lüfter reinigen | `print_hours` | 300 h | Alle Modelle | Hotend-Lüfter, Bauteilkühler, Kammerlüfter, Aux-Lüfter |
| HEPA-Filter wechseln | `total_hours` | 250 h | X1, X1C, X1E | Bambu Wiki: alle 3 Monate bei 8 h/Tag |
| Aktivkohle-Filter wechseln | `total_hours` | 250 h | X1, X1C, X1E, P1S, H2D | Bambu Wiki: alle 3 Monate bei 8 h/Tag |

### 🧲 AMS

| Aufgabe | Trigger | Standard | Gilt für | Bedingung |
|---|---|---|---|---|
| Purge Wiper reinigen | `print_count` | 50 Drucke | Alle Modelle mit AMS | Nur wenn AMS vorhanden (`requires_ams`) |
| AMS Getriebe / Rollen reinigen | `print_hours` | 300 h | Alle Modelle mit AMS | Nur wenn AMS vorhanden (`requires_ams`) |

### 📐 Kalibrierung

| Aufgabe | Trigger | Standard | Gilt für |
|---|---|---|---|
| Vibrationskompensation (Resonance) | `print_hours` | 300 h | Alle Modelle |
| Fluss-Kalibrierung | `print_hours` | 50 h | Alle Modelle |

### 🔆 Laser (H2D)

| Aufgabe | Trigger | Standard | Gilt für |
|---|---|---|---|
| Laserkopf Linse & Lüfter reinigen | `laser_hours` | 20 h | H2D |
| Laserkopf Grundreinigung | `laser_hours` | 100 h | H2D |
| Laserbett reinigen | `laser_jobs` | 10 Jobs | H2D |
| Lasersicherheitsscheibe prüfen | `laser_hours` | 100 h | H2D |

### 🔁 H2C Vortek

| Aufgabe | Trigger | Standard | Gilt für |
|---|---|---|---|
| Rack-Führungen schmieren | `total_hours` | 500 h | H2C |
| Hotend-Slots auf Verschleiß prüfen | `total_hours` | 200 h | H2C |

---

## Wie wird ausgelöst?

```
HA Update-Zyklus (60 s)
  └─ _update_runtime_trackers()   → Zähler inkrementieren
  └─ _update_maintenance_values()
       └─ Für jede Aufgabe:
            since_reset = max(0, current_value − baseline)
            if since_reset >= interval:
                → Benachrichtigung senden (max. 1× pro 24 h)
```

- **`total_hours`-Tasks** vergleichen `bambu_total_hours` (absoluter ha-bambulab-Sensor) minus der beim letzten Reset gespeicherten Baseline.
- **Alle anderen Tasks** vergleichen den internen Zähler (seit letztem Reset).
- Beim ersten Start wird automatisch eine Baseline gesetzt → keine Fehlauslösung aus historischen Daten.

---

## Reset-Verhalten

| Szenario | Was passiert |
|---|---|
| Aufgabe manuell zurücksetzen | Baseline = aktueller Zählerwert; `value = 0` |
| `reset_counter=True` (Düsenwechsel) | Zähler wird auf 0 gesetzt; Baselines **aller Aufgaben mit demselben Trigger** werden auf 0 zurückgesetzt |
| `total_hours`-Aufgabe zurücksetzen | Wenn `bambu_total_hours` verfügbar: Baseline = `bambu_total_hours` (absolut). Sonst: Baseline = interner `print_hours`-Zähler |
| HA-Neustart | Letzte Baselines und Zählerstände bleiben im `.storage`-File erhalten |

---

## Modell-Filterung

| Kriterium | Bedeutung |
|---|---|
| `models: None` | Gilt für alle Drucker |
| `models: ["X1C", ...]` | Gilt nur für die aufgelisteten Modelle |
| `requires_ams: True` | Wird nur erstellt wenn ein AMS-Gerät erkannt wurde |
| `single_nozzle_only: True` | Wird nicht erstellt wenn das Modell eine Dualdüse hat (H2D) |

Unbekannte Modelle (nicht in `PRINTER_FEATURES`) erhalten alle generischen Tasks (`models: None`) und werden als Einzeldüsen-Drucker behandelt.
