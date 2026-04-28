"""Constants for Bambu Print Tracker integration."""

DOMAIN = "bambu_companion"
BAMBU_LAB_DOMAIN = "bambu_lab"

# Frontend / Lovelace
URL_BASE = "/bambu_companion_static"
BAMBU_COMPANION_CARDS = [
    {
        "filename": "bambu-companion-cards.js",
        "version": "1.3.5",
        "name": "Bambu Companion Cards",
    }
]

# Storage
STORAGE_VERSION = 1
DEFAULT_MAX_HISTORY = 0  # 0 = unbegrenzt

# Defaults
DEFAULT_ELECTRICITY_PRICE = 0.35
DEFAULT_FILAMENT_COST_PER_KG = 25.00
DEFAULT_CURRENCY = "€"
DEFAULT_FILAMENT_UNIT = "kg"
DEFAULT_NOTIFY_INTERVAL = 5
DEFAULT_QUIET_FROM = "22:00"
DEFAULT_QUIET_TO = "07:00"
DEFAULT_PRINTER_NAME = "Bambu Lab"

# Config / Options keys
CONF_DEVICE_ID = "device_id"
CONF_AMS_DEVICE_IDS = "ams_device_ids"
CONF_ELECTRICITY_PRICE = "electricity_price"
CONF_ELECTRICITY_SENSOR = "electricity_sensor"
CONF_ENERGY_SENSOR = "energy_sensor"
CONF_FILAMENT_COST = "filament_cost"
CONF_CURRENCY = "currency"
CONF_FILAMENT_UNIT = "filament_unit"
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_NOTIFY_INTERVAL = "notify_interval"
CONF_QUIET_FROM = "quiet_from"
CONF_QUIET_TO = "quiet_to"
CONF_PRINTER_DISPLAY_NAME = "printer_display_name"
CONF_MAX_HISTORY = "max_history"
CONF_MAINTENANCE_INTERVALS = "maintenance_intervals"

# Per-channel notification events (multi-select lists)
# Each list contains event keys: "start", "progress", "done", "error", "maintenance"
CONF_NOTIFY_MOBILE_EVENTS = "notify_mobile_events"   # events sent to phone
CONF_NOTIFY_HA_EVENTS = "notify_ha_events"            # events shown in HA notifications

DEFAULT_NOTIFY_MOBILE_EVENTS: list[str] = []
DEFAULT_NOTIFY_HA_EVENTS: list[str] = ["done", "nozzle_change"]

# Custom text keys
CONF_TEXT_START_TITLE = "text_start_title"
CONF_TEXT_PROGRESS_TITLE = "text_progress_title"
CONF_TEXT_DONE_TITLE = "text_done_title"
CONF_TEXT_ERROR_TITLE = "text_error_title"
CONF_TEXT_MAINT_TITLE = "text_maint_title"
CONF_TEXT_RESET_TITLE = "text_reset_title"
CONF_TEXT_START_MSG = "text_start_msg"
CONF_TEXT_PROGRESS_MSG = "text_progress_msg"
CONF_TEXT_DONE_MSG = "text_done_msg"
CONF_TEXT_ERROR_MSG = "text_error_msg"
CONF_TEXT_MAINT_MSG = "text_maint_msg"
CONF_TEXT_RESET_MSG = "text_reset_msg"
CONF_TEXT_BTN_DONE = "text_btn_done"
CONF_TEXT_BTN_SNOOZE = "text_btn_snooze"
CONF_TEXT_BTN_CANCEL = "text_btn_cancel"
CONF_TEXT_BTN_RESET_CONFIRM = "text_btn_reset_confirm"
CONF_TEXT_BTN_RESET_CANCEL = "text_btn_reset_cancel"
CONF_TEXT_BTN_CAMERA = "text_btn_camera"

DEFAULT_TEXTS = {
    CONF_TEXT_START_TITLE: "🚀 {drucker} – Druck gestartet",
    CONF_TEXT_START_MSG: "{name} wird jetzt gedruckt.",
    CONF_TEXT_PROGRESS_TITLE: "{drucker} – {name} | {progress}%",
    CONF_TEXT_DONE_TITLE: "✅ {drucker} – Druck fertig – {name}",
    CONF_TEXT_ERROR_TITLE: "❌ {drucker} – Druckfehler – {name}",
    CONF_TEXT_MAINT_TITLE: "🔧 {drucker} – Wartung fällig – {wartung}",
    CONF_TEXT_RESET_TITLE: "⚠️ {drucker} – {wartung} wirklich zurücksetzen?",
    CONF_TEXT_PROGRESS_MSG: "Fortschritt: {progress}% ⏳ Verbleibend: {remaining}",
    CONF_TEXT_DONE_MSG: "⏱️ Dauer: {duration}\n📊 {weight} · {energy}\n💰 {cost}",
    CONF_TEXT_ERROR_MSG: "⚠️ Abgebrochen bei {progress}%\n⏱️ {duration}",
    CONF_TEXT_MAINT_MSG: "{wartung} hat {stunden}h erreicht (Intervall: {intervall}h)",
    CONF_TEXT_RESET_MSG: "{wartung} hat aktuell {stunden}h. Wirklich auf 0 zurücksetzen?",
    CONF_TEXT_BTN_DONE: "✅ Erledigt",
    CONF_TEXT_BTN_SNOOZE: "⏰ Erinnern in...",
    CONF_TEXT_BTN_CANCEL: "❌ Abbrechen",
    CONF_TEXT_BTN_RESET_CONFIRM: "✅ Ja, zurücksetzen",
    CONF_TEXT_BTN_RESET_CANCEL: "❌ Abbrechen",
    CONF_TEXT_BTN_CAMERA: "📷 Kamera",
}

# Print status values
PRINT_STATUS_IDLE = "idle"
PRINT_STATUS_PRINTING = "printing"
PRINT_STATUS_PAUSE = "pause"
PRINT_STATUS_FAILED = "failed"
PRINT_STATUS_FINISH = "finish"

ACTIVE_PRINT_STATUSES = {PRINT_STATUS_PRINTING, PRINT_STATUS_PAUSE}
TERMINAL_PRINT_STATUSES = {PRINT_STATUS_FAILED, PRINT_STATUS_FINISH}

# Printer model features
PRINTER_FEATURES: dict[str, dict] = {
    "X1": {
        "chamber_fan": True,
        "lidar": True,
        "dual_nozzle": False,
        "laser": False,
        "vortek": False,
        "target_chamber_temp": False,
        "secondary_aux": False,
        "airduct": False,
        "ams_lite": False,
    },
    "X1C": {
        "chamber_fan": True,
        "lidar": True,
        "dual_nozzle": False,
        "laser": False,
        "vortek": False,
        "target_chamber_temp": False,
        "secondary_aux": False,
        "airduct": False,
        "ams_lite": False,
    },
    "X1E": {
        "chamber_fan": True,
        "lidar": True,
        "dual_nozzle": False,
        "laser": False,
        "vortek": False,
        "target_chamber_temp": True,
        "secondary_aux": False,
        "airduct": False,
        "ams_lite": False,
    },
    "P1P": {
        "chamber_fan": False,
        "lidar": False,
        "dual_nozzle": False,
        "laser": False,
        "vortek": False,
        "target_chamber_temp": False,
        "secondary_aux": False,
        "airduct": False,
        "ams_lite": False,
    },
    "P1S": {
        "chamber_fan": False,
        "lidar": False,
        "dual_nozzle": False,
        "laser": False,
        "vortek": False,
        "target_chamber_temp": False,
        "secondary_aux": False,
        "airduct": False,
        "ams_lite": False,
    },
    "P2S": {
        "chamber_fan": False,
        "lidar": False,
        "dual_nozzle": False,
        "laser": False,
        "vortek": False,
        "target_chamber_temp": False,
        "secondary_aux": True,
        "airduct": True,
        "ams_lite": False,
    },
    "A1": {
        "chamber_fan": False,
        "lidar": False,
        "dual_nozzle": False,
        "laser": False,
        "vortek": False,
        "target_chamber_temp": False,
        "secondary_aux": False,
        "airduct": False,
        "ams_lite": True,
    },
    "A1MINI": {
        "chamber_fan": False,
        "lidar": False,
        "dual_nozzle": False,
        "laser": False,
        "vortek": False,
        "target_chamber_temp": False,
        "secondary_aux": False,
        "airduct": False,
        "ams_lite": True,
    },
    "H2D": {
        "chamber_fan": True,
        "lidar": False,
        "dual_nozzle": True,
        "laser": True,
        "vortek": False,
        "target_chamber_temp": True,
        "secondary_aux": False,
        "airduct": True,
        "ams_lite": False,
    },
    "H2C": {
        "chamber_fan": True,
        "lidar": False,
        "dual_nozzle": False,
        "laser": False,
        "vortek": True,
        "target_chamber_temp": False,
        "secondary_aux": False,
        "airduct": True,
        "ams_lite": False,
    },
}

# Maintenance task definitions
# trigger types: print_hours, total_hours, print_count, laser_hours, laser_jobs, nozzle_hours
# wiki: Bambu Lab Wiki link for reference (exposed as sensor attribute)
MAINTENANCE_TASKS: list[dict] = [
    # Nozzle & Hotend
    {"key": "nozzle_clean", "name": "Druckkopf Düse reinigen", "default_interval": 200, "trigger": "nozzle_hours", "models": None, "single_nozzle_only": True,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#nozzle"},
    {"key": "nozzle_replace", "name": "Druckkopf Düse gewechselt (Stundenzähler zurücksetzen)", "default_interval": 800, "trigger": "nozzle_hours", "models": None, "single_nozzle_only": True, "reset_counter": True,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#nozzle"},
    {"key": "left_nozzle_clean", "name": "Druckkopf Linke Düse reinigen", "default_interval": 200, "trigger": "nozzle_hours", "models": ["H2D"],
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#nozzle"},
    {"key": "left_nozzle_replace", "name": "Druckkopf Linke Düse gewechselt (Stundenzähler zurücksetzen)", "default_interval": 800, "trigger": "nozzle_hours", "models": ["H2D"], "reset_counter": True, "counter_key": "left_nozzle_hours",
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#nozzle"},
    {"key": "right_nozzle_clean", "name": "Druckkopf Rechte Düse reinigen", "default_interval": 200, "trigger": "nozzle_hours", "models": ["H2D"],
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#nozzle"},
    {"key": "right_nozzle_replace", "name": "Druckkopf Rechte Düse gewechselt (Stundenzähler zurücksetzen)", "default_interval": 800, "trigger": "nozzle_hours", "models": ["H2D"], "reset_counter": True, "counter_key": "right_nozzle_hours",
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#nozzle"},
    # Bambu Wiki: blade should be checked every 3-5 rolls (≈ 20 prints); ~5000-7000 cuts before replacement
    {"key": "filament_cutter", "name": "Druckkopf Schneidmesser prüfen / wechseln", "default_interval": 20, "trigger": "print_count", "models": None,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#filament-cutter"},
    {"key": "ptfe_tube", "name": "Druckkopf PTFE-Tube prüfen / wechseln", "default_interval": 500, "trigger": "print_hours", "models": None,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#ptfe-tube-coupler"},
    {"key": "heatbreak", "name": "Druckkopf Hotend / Heatbreak reinigen", "default_interval": 500, "trigger": "print_hours", "models": None,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#hotend-cleaning"},
    # Motion
    # Bambu Wiki: Y/Z linear rods – check monthly, anti-rust every 3 months. NOT the X carbon rods (those are separate).
    {"key": "lube_linear", "name": "Y/Z-Linearschienen reinigen & konservieren", "default_interval": 300, "trigger": "print_hours", "models": None,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#y-axis-and-z-axis-linear-rods-and-bearings"},
    # Bambu Wiki: Z lead screws – grease every 3 months
    {"key": "lube_z", "name": "Z-Gewindespindeln schmieren", "default_interval": 500, "trigger": "print_hours", "models": None,
     "wiki": "https://wiki.bambulab.com/en/general/lead-screws-lubrication"},
    # Bambu Wiki: X carbon rods – clean with IPA every 5 rolls of ABS/ASA or monthly. NEVER use oil or grease!
    {"key": "carbon_rods", "name": "Carbon-Stangen reinigen (IPA, kein Öl!)", "default_interval": 200, "trigger": "print_hours", "models": ["X1", "X1C", "X1E", "P1S"],
     "wiki": "https://wiki.bambulab.com/en/general/carbon-rods-clearance"},
    {"key": "belt", "name": "Riemenspannung prüfen (X & Y)", "default_interval": 500, "trigger": "print_hours", "models": None,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/belt-tension"},
    {"key": "extruder_gear", "name": "Druckkopf Extruder-Zahnrad reinigen", "default_interval": 300, "trigger": "print_hours", "models": None,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#extruder-assembly"},
    {"key": "toolhead_cable", "name": "Druckkopf Kabel prüfen", "default_interval": 1000, "trigger": "print_hours", "models": None,
     "wiki": None},
    # Bed
    {"key": "clean_bed", "name": "Druckbett reinigen", "default_interval": 20, "trigger": "print_count", "models": None,
     "wiki": None},
    # Fans & Filters
    # Bambu Wiki: clean hotend fan, part cooling fan, chamber fan, aux fan in one session (weekly check recommended)
    {"key": "fans_clean", "name": "Alle Lüfter reinigen", "default_interval": 300, "trigger": "print_hours", "models": None,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#part-cooling-fans"},
    # Bambu Wiki: replace activated carbon air filter every 3 months (8h/day usage)
    {"key": "hepa_filter", "name": "Kammer-HEPA-Filter wechseln", "default_interval": 250, "trigger": "total_hours", "models": ["X1", "X1C", "X1E"],
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/replace-carbon-filter"},
    {"key": "carbon_filter", "name": "Aktivkohle-Filter wechseln", "default_interval": 250, "trigger": "total_hours", "models": ["X1", "X1C", "X1E", "P1S", "H2D"],
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/replace-carbon-filter"},
    # AMS
    {"key": "ams_wiper", "name": "Purge Wiper reinigen", "default_interval": 50, "trigger": "print_count", "models": None, "requires_ams": True,
     "wiki": "https://wiki.bambulab.com/en/x1/maintenance/basic-maintenance#nozzle-wiper"},
    {"key": "ams_gears", "name": "AMS Getriebe / Rollen reinigen", "default_interval": 300, "trigger": "print_hours", "models": None, "requires_ams": True,
     "wiki": "https://wiki.bambulab.com/en/ams/maintenance/basic-maintenance"},
    # Calibration
    {"key": "resonance_cal", "name": "Vibrationskompensation (Resonance)", "default_interval": 300, "trigger": "print_hours", "models": None,
     "wiki": None},
    {"key": "flow_cal", "name": "Fluss-Kalibrierung", "default_interval": 50, "trigger": "print_hours", "models": None,
     "wiki": None},
    # Laser (H2D)
    {"key": "laser_lens", "name": "Laserkopf Linse & Lüfter reinigen", "default_interval": 20, "trigger": "laser_hours", "models": ["H2D"], "wiki": None},
    {"key": "laser_deep", "name": "Laserkopf Grundreinigung", "default_interval": 100, "trigger": "laser_hours", "models": ["H2D"], "wiki": None},
    {"key": "laser_bed", "name": "Laserbett reinigen", "default_interval": 10, "trigger": "laser_jobs", "models": ["H2D"], "wiki": None},
    {"key": "laser_safety", "name": "Lasersicherheitsscheibe prüfen", "default_interval": 100, "trigger": "laser_hours", "models": ["H2D"], "wiki": None},
    # H2C Vortek
    {"key": "vortek_lube", "name": "Rack-Führungen schmieren", "default_interval": 500, "trigger": "total_hours", "models": ["H2C"], "wiki": None},
    {"key": "vortek_wear", "name": "Hotend-Slots auf Verschleiß prüfen", "default_interval": 200, "trigger": "total_hours", "models": ["H2C"], "wiki": None},
]

# Nozzle temperature threshold for nozzle_hours tracking
NOZZLE_ACTIVE_TEMP_THRESHOLD = 100  # °C

PLATFORMS = ["sensor", "button", "select", "text"]
