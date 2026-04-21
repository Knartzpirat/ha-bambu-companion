"""Constants for Bambu Print Tracker integration."""

DOMAIN = "bambu_print_tracker"
BAMBU_LAB_DOMAIN = "bambu_lab"

# Storage
STORAGE_VERSION = 1
DEFAULT_MAX_HISTORY = 50

# Defaults
DEFAULT_ELECTRICITY_PRICE = 0.30
DEFAULT_FILAMENT_COST_PER_KG = 25.00
DEFAULT_CURRENCY = "€"
DEFAULT_FILAMENT_UNIT = "kg"
DEFAULT_NOTIFY_INTERVAL = 5
DEFAULT_QUIET_FROM = "22:00"
DEFAULT_QUIET_TO = "07:00"
DEFAULT_PRINTER_NAME = "Bambu Lab"
DEFAULT_LOW_FILAMENT_THRESHOLD = 15

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
CONF_LOW_FILAMENT_THRESHOLD = "low_filament_threshold"
CONF_MAINTENANCE_INTERVALS = "maintenance_intervals"

# Custom text keys
CONF_TEXT_PROGRESS_TITLE = "text_progress_title"
CONF_TEXT_DONE_TITLE = "text_done_title"
CONF_TEXT_ERROR_TITLE = "text_error_title"
CONF_TEXT_MAINT_TITLE = "text_maint_title"
CONF_TEXT_RESET_TITLE = "text_reset_title"
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
MAINTENANCE_TASKS: list[dict] = [
    # Nozzle & Hotend
    {"key": "nozzle_clean", "name": "Düse reinigen / wechseln", "default_interval": 200, "trigger": "nozzle_hours", "models": None},
    {"key": "left_nozzle_clean", "name": "Linke Düse reinigen / wechseln", "default_interval": 200, "trigger": "nozzle_hours", "models": ["H2D"]},
    {"key": "right_nozzle_clean", "name": "Rechte Düse reinigen / wechseln", "default_interval": 200, "trigger": "nozzle_hours", "models": ["H2D"]},
    {"key": "ptfe_tube", "name": "PTFE-Tube prüfen/wechseln", "default_interval": 500, "trigger": "print_hours", "models": None},
    {"key": "heatbreak", "name": "Heatbreak reinigen", "default_interval": 500, "trigger": "print_hours", "models": None},
    # Motion
    {"key": "lube_xy", "name": "X/Y Linearschienen schmieren", "default_interval": 300, "trigger": "print_hours", "models": None},
    {"key": "lube_z", "name": "Z-Achse schmieren", "default_interval": 500, "trigger": "print_hours", "models": None},
    {"key": "carbon_rods", "name": "Carbon-Stangen reinigen & ölen", "default_interval": 200, "trigger": "print_hours", "models": ["X1C", "P1S", "H2D"]},
    {"key": "belt_x", "name": "Riemenspannung prüfen (X)", "default_interval": 500, "trigger": "print_hours", "models": None},
    {"key": "belt_y", "name": "Riemenspannung prüfen (Y)", "default_interval": 500, "trigger": "print_hours", "models": None},
    {"key": "extruder_gear", "name": "Extruder-Zahnrad reinigen", "default_interval": 300, "trigger": "print_hours", "models": None},
    {"key": "toolhead_cable", "name": "Toolhead-Kabel prüfen", "default_interval": 1000, "trigger": "print_hours", "models": None},
    # Bed
    {"key": "clean_bed", "name": "Druckbett reinigen (IPA)", "default_interval": 20, "trigger": "print_count", "models": None},
    {"key": "flip_bed", "name": "Druckbett wenden", "default_interval": 100, "trigger": "print_count", "models": None},
    {"key": "inspect_bed", "name": "Druckbett auf Verschleiß prüfen", "default_interval": 500, "trigger": "print_count", "models": None},
    # Fans & Filters
    {"key": "parts_fan", "name": "Teilekühler-Lüfter reinigen", "default_interval": 300, "trigger": "print_hours", "models": None},
    {"key": "hotend_fan", "name": "Hotend-Lüfter reinigen", "default_interval": 300, "trigger": "print_hours", "models": None},
    {"key": "hepa_filter", "name": "Kammer-HEPA-Filter wechseln", "default_interval": 250, "trigger": "total_hours", "models": ["X1C", "P1S", "H2D"]},
    {"key": "carbon_filter", "name": "Aktivkohle-Filter wechseln", "default_interval": 250, "trigger": "total_hours", "models": ["X1C", "P1S", "H2D"]},
    {"key": "chamber_fan", "name": "Kammerlüfter reinigen", "default_interval": 500, "trigger": "print_hours", "models": ["X1C", "P1S", "H2D"]},
    # AMS
    {"key": "ams_wiper", "name": "Purge Wiper / Schneidklinge reinigen", "default_interval": 50, "trigger": "print_count", "models": None, "requires_ams": True},
    {"key": "ams_cutter", "name": "AMS Schneidmesser ersetzen", "default_interval": 500, "trigger": "print_count", "models": None, "requires_ams": True},
    {"key": "ams_gears", "name": "AMS Getriebe/Rollen reinigen", "default_interval": 300, "trigger": "print_hours", "models": None, "requires_ams": True},
    # Calibration
    {"key": "resonance_cal", "name": "Vibrationskompensation (Resonance)", "default_interval": 300, "trigger": "print_hours", "models": None},
    {"key": "flow_cal", "name": "Fluss-Kalibrierung", "default_interval": 50, "trigger": "print_hours", "models": None},
    {"key": "first_layer_cal", "name": "Erst-Schicht-Kalibrierung", "default_interval": 100, "trigger": "print_hours", "models": None},
    # Laser (H2D)
    {"key": "laser_lens", "name": "Laserkopf-Linse reinigen", "default_interval": 20, "trigger": "laser_hours", "models": ["H2D"]},
    {"key": "laser_air", "name": "Lasermodul Luftdüse prüfen", "default_interval": 50, "trigger": "laser_hours", "models": ["H2D"]},
    {"key": "laser_bed", "name": "Laserbett reinigen (Rückstände)", "default_interval": 10, "trigger": "laser_jobs", "models": ["H2D"]},
    {"key": "laser_inspect", "name": "Lasermodul auf Beschädigung prüfen", "default_interval": 200, "trigger": "laser_hours", "models": ["H2D"]},
    {"key": "laser_safety", "name": "Lasersicherheitsscheibe prüfen", "default_interval": 100, "trigger": "laser_hours", "models": ["H2D"]},
    # H2C Vortek
    {"key": "vortek_lube", "name": "Rack-Führungen schmieren", "default_interval": 500, "trigger": "total_hours", "models": ["H2C"]},
    {"key": "vortek_wear", "name": "Hotend-Slots auf Verschleiß prüfen", "default_interval": 200, "trigger": "total_hours", "models": ["H2C"]},
]

# Nozzle temperature threshold for nozzle_hours tracking
NOZZLE_ACTIVE_TEMP_THRESHOLD = 100  # °C

PLATFORMS = ["sensor", "button"]
