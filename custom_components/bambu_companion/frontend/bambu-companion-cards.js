/**
 * Bambu Companion Cards for Home Assistant
 * Three custom Lovelace cards:
 *   bambu-companion-overview-card
 *   bambu-companion-maintenance-card
 *   bambu-companion-history-card
 */
const VERSION = "1.5.8";

// ── Helpers ────────────────────────────────────────────────────────────────────

// Case-insensitive entity resolver – handles uppercase serials stored in HA registry
function resolveEntityId(hass, target) {
    if (hass.states[target]) return target;
    const lower = target.toLowerCase();
    for (const eid of Object.keys(hass.states)) {
        if (eid.toLowerCase() === lower) return eid;
    }
    return target; // fallback (will be "unavailable")
}

/**
 * Known stat keys – used for suffix-matching when entity_id has no serial.
 * Covers all BcStatSensor keys from sensor.py.
 */
const KNOWN_STAT_KEYS = [
    "print_status", "print_progress",
    "total_prints", "successful_prints", "failed_prints",
    "total_print_time", "total_energy", "total_filament", "total_cost",
    "monthly_cost", "monthly_prints",
    "last_print_duration", "last_print_cost",
    "total_filament_cost", "total_energy_cost",
    "left_nozzle_hours", "right_nozzle_hours", "nozzle_hours", "laser_hours",
];

/**
 * Build a {stat_key: entity_id} map for a given serial.
 *
 * Strategy 0: entity registry filtered by platform=bambu_companion + device_id.
 *   Uses serial-substring extract OR known-key suffix matching.
 *   Most robust: works even when HA renamed entity_ids (old registry entries).
 * Strategy 1: entity registry, platform-filtered, serial-substring only.
 * Strategy 2: entity registry without platform filter.
 * Strategy 3: hass.states scan (no entity registry needed).
 */
function buildEntityMap(hass, serial) {
    const map = {};
    if (!hass || !serial) return map;
    const serialLower = serial.toLowerCase();
    const needle = "_" + serialLower + "_";

    const _extract = (eidLower) => {
        const idx = eidLower.indexOf(needle);
        if (idx === -1) return null;
        const key = eidLower.slice(idx + needle.length);
        return key || null;
    };

    const _extractOrSuffix = (eidLower) => {
        // Try serial-substring first
        const k = _extract(eidLower);
        if (k) return k;
        // Fallback: entity_id ends with _<known_key>
        for (const key of KNOWN_STAT_KEYS) {
            if (eidLower.endsWith("_" + key)) return key;
        }
        return null;
    };

    // Strategy 0: device-registry match → platform + device_id
    // Handles cases where HA stored a different entity_id in the registry
    if (hass.entities && hass.devices) {
        let targetDeviceId = null;
        for (const [did, device] of Object.entries(hass.devices)) {
            for (const [domain, identifier] of (device.identifiers ?? [])) {
                if (domain === "bambu_companion" && String(identifier).toLowerCase() === serialLower) {
                    targetDeviceId = did;
                    break;
                }
            }
            if (targetDeviceId) break;
        }
        if (targetDeviceId) {
            for (const [eid, entry] of Object.entries(hass.entities)) {
                if (entry.platform !== "bambu_companion") continue;
                if (entry.device_id !== targetDeviceId) continue;
                const key = _extractOrSuffix(eid.toLowerCase());
                if (key && !map[key]) map[key] = eid;
            }
        }
        if (Object.keys(map).length) return map;
    }

    // Strategy 0b: platform-filtered, no device filter, suffix matching
    // Catches bambu_companion entities not associated with a device (old registry entries)
    if (hass.entities) {
        for (const [eid, entry] of Object.entries(hass.entities)) {
            if (entry.platform !== "bambu_companion") continue;
            const key = _extractOrSuffix(eid.toLowerCase());
            if (key && !map[key]) map[key] = eid;
        }
        if (Object.keys(map).length) return map;
    }

    // Strategy 1: entity registry, platform-filtered, serial-substring
    if (hass.entities) {
        for (const [eid, entry] of Object.entries(hass.entities)) {
            if (entry.platform !== "bambu_companion") continue;
            const key = _extract(eid.toLowerCase());
            if (key) map[key] = eid;
        }
        if (Object.keys(map).length) return map;

        // Strategy 2: entity registry without platform filter
        for (const [eid] of Object.entries(hass.entities)) {
            const key = _extract(eid.toLowerCase());
            if (key) map[key] = eid;
        }
        if (Object.keys(map).length) return map;
    }

    // Strategy 3: scan hass.states (works even without entity registry)
    for (const eid of Object.keys(hass.states ?? {})) {
        const key = _extract(eid.toLowerCase());
        if (key) map[key] = eid;
    }

    return map;
}

/** Find any candidate entity_ids that contain the serial (for diagnostics). */
function _findCandidates(hass, serialLower) {
    const needle = serialLower;
    const found = new Set();
    if (hass.entities) {
        for (const eid of Object.keys(hass.entities)) {
            if (eid.toLowerCase().includes(needle)) found.add(eid);
        }
    }
    for (const eid of Object.keys(hass.states ?? {})) {
        if (eid.toLowerCase().includes(needle)) found.add(eid);
    }
    return [...found].sort();
}

function getState(hass, entityId) {
    const resolved = resolveEntityId(hass, entityId);
    return hass.states[resolved]?.state ?? "unavailable";
}

function getNum(hass, entityId) {
    const v = parseFloat(getState(hass, entityId));
    return isNaN(v) ? 0 : v;
}

function statusColor(status) {
    return {
        printing: "var(--success-color, #4caf50)",
        pause: "var(--warning-color, #ff9800)",
        failed: "var(--error-color,   #f44336)",
        finish: "var(--info-color,    #2196f3)",
    }[status] ?? "var(--secondary-text-color)";
}

const SHARED_STYLE = `
  :host { display: block; height: 100%; }
  ha-card { padding: 16px; box-sizing: border-box; height: 100%; }
  .card-header {
    display: flex; align-items: center; gap: 10px;
    font-size: 1.1em; font-weight: 500; margin-bottom: 16px;
  }
  .section-label {
    font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--secondary-text-color); margin-bottom: 8px;
  }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .tile {
    background: var(--secondary-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px; padding: 10px; text-align: center;
  }
  .tile-value { font-size: 1.35em; font-weight: 600; }
  .tile-label { font-size: 0.7em; color: var(--secondary-text-color); margin-top: 2px; }
  hr { border: none; border-top: 1px solid var(--divider-color); margin: 12px 0; }
  .ok      { color: var(--success-color, #4caf50); }
  .warning { color: var(--warning-color, #ff9800); }
  .error   { color: var(--error-color,   #f44336); }
  .muted   { color: var(--secondary-text-color); }
`;


// ── Editor Helpers ────────────────────────────────────────────────────────────

const SHARED_EDITOR_STYLE = `
  .row { display:flex; flex-direction:column; gap:6px; margin-bottom:12px; }
  label { font-size:0.85em; color:var(--secondary-text-color); }
  select, input {
    width:100%; padding:8px; box-sizing:border-box;
    border:1px solid var(--divider-color);
    border-radius:4px; background:var(--card-background-color);
    color:var(--primary-text-color); font-size:0.95em;
  }
  .hint { font-size:0.75em; color:var(--secondary-text-color); margin-top:2px; }
`;

function _findPrinters(hass) {
    const result = [];
    const seen = new Set(); // always stores UPPERCASE serials

    // Method 1 (most reliable): scan device registry for devices owned by bambu_companion.
    // Every install has a device with identifiers = [["bambu_companion", serial]].
    if (hass.devices) {
        for (const device of Object.values(hass.devices)) {
            for (const [domain, identifier] of (device.identifiers ?? [])) {
                if (domain !== "bambu_companion") continue;
                const key = identifier.toUpperCase();
                if (seen.has(key)) continue;
                seen.add(key);
                result.push({
                    serial: identifier,
                    label: device.name_by_user || device.name || identifier,
                });
            }
        }
    }

    // Method 2: scan hass.entities (entity registry) for bambu_companion sensors
    // This catches entities where HA assigned a different entity_id than expected
    if (hass.entities) {
        for (const [eid, entry] of Object.entries(hass.entities)) {
            if (entry.platform !== "bambu_companion") continue;
            const m = eid.match(/^sensor\.[a-z_]+_(.+?)_print_status$/i);
            if (!m) continue;
            const key = m[1].toUpperCase();
            if (seen.has(key)) continue;
            // Resolve label via device registry
            let label = m[1];
            if (entry.device_id && hass.devices) {
                const device = hass.devices[entry.device_id];
                if (device) label = device.name_by_user || device.name || m[1];
            }
            seen.add(key);
            result.push({ serial: m[1], label });
        }
    }

    // Method 3: scan hass.states for bc_ entity_id pattern (fallback for older HA versions)
    for (const entityId of Object.keys(hass.states ?? {})) {
        const m = entityId.match(/^sensor\.bc_(.+?)_print_status$/i);
        const key = m?.[1]?.toUpperCase();
        if (!m || seen.has(key)) continue;
        seen.add(key);
        let label = m[1];
        if (hass.entities && hass.devices) {
            const entry = hass.entities[entityId];
            if (entry?.device_id) {
                const device = hass.devices[entry.device_id];
                if (device) label = device.name_by_user || device.name || m[1];
            }
        }
        result.push({ serial: m[1], label });
    }

    result.sort((a, b) => a.label.localeCompare(b.label));
    return result;
}

function _printerSelect(printers, current) {
    if (!printers.length) {
        return `<select id="serial"><option value="">– Kein Bambu Companion Drucker gefunden –</option></select>
                <div class="hint">Bitte zuerst die Integration einrichten.</div>`;
    }
    const opts = printers.map(({ serial, label }) =>
        `<option value="${serial}"${serial === current ? " selected" : ""}>${label}</option>`
    ).join("");
    return `<select id="serial"><option value="">– Drucker wählen –</option>${opts}</select>`;
}

// ── Overview Card ─────────────────────────────────────────────────────────────

class BambuCompanionOverviewCard extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }); }

    setConfig(config) {
        this._config = config;
        this._entityMap = {};
    }

    set hass(hass) {
        this._hass = hass;
        // Rebuild entity map on each hass update so we always use the actual entity_ids
        if (this._config?.serial) {
            this._entityMap = buildEntityMap(hass, this._config.serial);
        }
        this._render();
    }

    /** Return the actual entity_id for a stat key, with fallback to bc_ pattern. */
    _e(key) {
        return this._entityMap?.[key]
            ?? resolveEntityId(this._hass, `sensor.bc_${this._config.serial.toLowerCase()}_${key}`);
    }

    _render() {
        if (!this._config?.serial) {
            this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:var(--secondary-text-color)">Bitte einen Drucker in den Karteneinstellungen auswählen.</div></ha-card>`;
            return;
        }
        if (!this._hass || !this._config) return;
        const h = this._hass;
        const { serial, currency = "€", printer_name = serial } = this._config;

        const statusEid = this._e("print_status");
        const status = getState(h, statusEid);

        const progress = getNum(h, this._e("print_progress"));
        const totalPrints = getNum(h, this._e("total_prints"));
        const successPrints = getNum(h, this._e("successful_prints"));
        const failedPrints = getNum(h, this._e("failed_prints"));
        const printTime = getNum(h, this._e("total_print_time"));
        const filament = getNum(h, this._e("total_filament"));
        const energy = getNum(h, this._e("total_energy"));
        const totalCost = getNum(h, this._e("total_cost"));
        const monthlyPrints = getNum(h, this._e("monthly_prints"));
        const monthlyCost = getNum(h, this._e("monthly_cost"));
        const lastDuration = getNum(h, this._e("last_print_duration"));
        const lastCost = getNum(h, this._e("last_print_cost"));

        // Show diagnostic card when entity is truly missing
        if (status === "unavailable" && !h.states[statusEid]) {
            const serialLower = serial.toLowerCase();
            const mapKeys = Object.keys(this._entityMap || {});

            // Find device_id for this serial
            let diagDeviceId = null;
            if (h.devices) {
                for (const [did, device] of Object.entries(h.devices)) {
                    for (const [domain, identifier] of (device.identifiers ?? [])) {
                        if (domain === "bambu_companion" && String(identifier).toLowerCase() === serialLower) { diagDeviceId = did; break; }
                    }
                    if (diagDeviceId) break;
                }
            }

            // Find ALL bambu_companion entities for this device
            const bcEntities = [];
            if (h.entities && diagDeviceId) {
                for (const [eid, entry] of Object.entries(h.entities)) {
                    if (entry.platform === "bambu_companion" && entry.device_id === diagDeviceId) {
                        bcEntities.push(eid);
                    }
                }
            }

            const candidates = _findCandidates(h, serialLower);
            const mapInfo = mapKeys.length
                ? `<b>${mapKeys.length} Keys in Entity-Map:</b><br>${mapKeys.sort().map(k => `&nbsp;&nbsp;<code>${k}</code> → <code>${this._entityMap[k]}</code>`).join("<br>")}`
                : `<b>Entity-Map leer</b> – Serial "${serial}" nirgends in entity_id gefunden`;
            const bcInfo = bcEntities.length
                ? `<b>${bcEntities.length} bambu_companion-Entities für dieses Gerät:</b><br>${bcEntities.sort().map(e => `&nbsp;&nbsp;<code>${e}</code>`).join("<br>")}`
                : diagDeviceId
                    ? `<b>Keine bambu_companion-Entities für device_id=${diagDeviceId}</b>`
                    : `<b>Gerät mit Serial "${serialLower}" nicht im device-registry gefunden</b>`;
            const candidateInfo = candidates.length
                ? `<b>${candidates.length} Entities mit Serial im entity_id:</b><br>${candidates.map(e => `&nbsp;&nbsp;<code>${e}</code>`).join("<br>")}`
                : `<b>Keine Entität mit "${serialLower}" im entity_id</b>`;
            console.warn(
                `[BambuCompanion] Sensor '${statusEid}' nicht in hass.states.\n` +
                `Serial: ${serial} | device_id: ${diagDeviceId} | entityMap: [${mapKeys.join(", ")}]\n` +
                `bc entities: [${bcEntities.join(", ")}]\n` +
                `Kandidaten: ${candidates.join(", ") || "keine"}`
            );
            this.shadowRoot.innerHTML = `
      <style>${SHARED_STYLE}
        code { background:var(--secondary-background-color); padding:1px 4px; border-radius:3px; font-size:0.82em; word-break:break-all; }
        .diag { font-size:0.78em; line-height:1.8; margin-top:8px; }
        hr { border:none; border-top:1px solid var(--divider-color); margin:8px 0; }
      </style>
      <ha-card>
        <div class="card-header">⚠️ ${printer_name} – print_status nicht gefunden</div>
        <div style="font-size:0.8em;color:var(--error-color,#f44336);margin-bottom:4px">
          Gesucht: <code>${statusEid}</code>
        </div>
        <div class="diag">${bcInfo}</div>
        <hr>
        <div class="diag">${mapInfo}</div>
        <hr>
        <div class="diag">${candidateInfo}</div>
        <hr>
        <div class="diag" style="color:var(--secondary-text-color)">
          <b>Nächste Schritte:</b><br>
          1. HA → Einstellungen → Geräte & Dienste → Bambu Companion → Entitäten prüfen<br>
          2. Deaktivierte Entitäten aktivieren<br>
          3. HA neu starten falls Entities fehlen<br>
          4. HA-Log nach "bambu_companion" durchsuchen
        </div>
      </ha-card>`;
            return;
        }

        const color = statusColor(status);
        const isPrinting = status === "printing" || status === "pause";

        this.shadowRoot.innerHTML = `
      <style>
        ${SHARED_STYLE}
        .status-dot {
          width: 11px; height: 11px; border-radius: 50%;
          background: ${color}; flex-shrink: 0;
        }
        .status-badge {
          font-size: 0.75em; padding: 2px 9px; border-radius: 12px;
          background: ${color}22; color: ${color};
          font-weight: 700; text-transform: capitalize; margin-left: auto;
        }
        .progress-bar {
          height: 4px; background: var(--secondary-background-color);
          border-radius: 2px; margin-bottom: 14px; overflow: hidden;
        }
        .progress-fill {
          height: 100%; border-radius: 2px;
          background: var(--primary-color);
          width: ${progress}%;
          transition: width 0.4s ease;
        }
        section { margin-bottom: 14px; }
        .tile[data-entity] { cursor: pointer; transition: transform 0.1s, box-shadow 0.1s; }
        .tile[data-entity]:hover { transform: translateY(-2px); box-shadow: 0 3px 8px rgba(0,0,0,0.15); }
        .tile[data-entity]:active { transform: scale(0.97); }
        .status-badge[data-entity] { cursor: pointer; }
        .status-badge[data-entity]:hover { opacity: 0.8; }
      </style>
      <ha-card>
        <div class="card-header">
          <div class="status-dot"></div>
          <span>📊 ${printer_name}</span>
          <div class="status-badge" data-entity="${this._e('print_status')}">${status}${isPrinting ? ` ${progress}%` : ""}</div>
        </div>

        ${isPrinting ? `<div class="progress-bar"><div class="progress-fill"></div></div>` : ""}

        <section>
          <div class="section-label">Drucke</div>
          <div class="grid-3">
            <div class="tile" data-entity="${this._e('total_prints')}"><div class="tile-value">${totalPrints}</div><div class="tile-label">Gesamt</div></div>
            <div class="tile" data-entity="${this._e('successful_prints')}"><div class="tile-value ok">${successPrints}</div><div class="tile-label">Erfolgreich</div></div>
            <div class="tile" data-entity="${this._e('failed_prints')}"><div class="tile-value error">${failedPrints}</div><div class="tile-label">Fehlgeschlagen</div></div>
          </div>
        </section>

        <section>
          <div class="section-label">Verbrauch gesamt</div>
          <div class="grid-3">
            <div class="tile" data-entity="${this._e('total_print_time')}"><div class="tile-value">${printTime.toFixed(1)} h</div><div class="tile-label">Druckzeit</div></div>
            <div class="tile" data-entity="${this._e('total_filament')}"><div class="tile-value">${filament.toFixed(0)} g</div><div class="tile-label">Filament</div></div>
            <div class="tile" data-entity="${this._e('total_energy')}"><div class="tile-value">${energy.toFixed(2)} kWh</div><div class="tile-label">Energie</div></div>
          </div>
        </section>

        <hr>

        <section>
          <div class="section-label">Diesen Monat</div>
          <div class="grid-2">
            <div class="tile" data-entity="${this._e('monthly_prints')}"><div class="tile-value">${monthlyPrints}</div><div class="tile-label">Drucke</div></div>
            <div class="tile" data-entity="${this._e('monthly_cost')}"><div class="tile-value">${monthlyCost.toFixed(2)} ${currency}</div><div class="tile-label">Kosten</div></div>
          </div>
        </section>

        <section>
          <div class="section-label">Letzter Druck</div>
          <div class="grid-2">
            <div class="tile" data-entity="${this._e('last_print_duration')}"><div class="tile-value">${lastDuration} min</div><div class="tile-label">Dauer</div></div>
            <div class="tile" data-entity="${this._e('last_print_cost')}"><div class="tile-value">${lastCost.toFixed(2)} ${currency}</div><div class="tile-label">Kosten</div></div>
          </div>
        </section>

        <div class="tile" style="text-align:center" data-entity="${this._e('total_cost')}">
          <div class="tile-value">${totalCost.toFixed(2)} ${currency}</div>
          <div class="tile-label">Gesamtkosten</div>
        </div>
      </ha-card>
    `;
        // Delegated click → open HA more-info dialog (history chart) once
        if (!this._clickListenerAdded) {
            this._clickListenerAdded = true;
            this.shadowRoot.addEventListener("click", e => {
                const target = e.target.closest("[data-entity]");
                if (target?.dataset.entity) {
                    this.dispatchEvent(new CustomEvent("hass-more-info", {
                        bubbles: true, composed: true,
                        detail: { entityId: target.dataset.entity },
                    }));
                }
            });
        }
    }

    getCardSize() { return 7; }
    getGridOptions() { return { columns: 12, rows: 10, min_columns: 6, min_rows: 3 }; }
    static getStubConfig() { return { serial: "", currency: "€", printer_name: "Bambu Drucker" }; }
    static getConfigElement() { return document.createElement("bambu-companion-overview-card-editor"); }
}


// ── Overview Card Editor ──────────────────────────────────────────────────────

class BambuCompanionOverviewCardEditor extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }); }

    setConfig(config) { this._config = config; this._render(); }
    set hass(hass) { this._hass = hass; this._render(); }

    _fire() {
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
    }

    _render() {
        if (!this._hass) return;
        const c = this._config || {};
        const printers = _findPrinters(this._hass);

        this.shadowRoot.innerHTML = `
      <style>${SHARED_EDITOR_STYLE}</style>
      <div class="row">
        <label>Drucker *</label>
        ${_printerSelect(printers, c.serial ?? "")}
      </div>
      <div class="row">
        <label>Druckername (Anzeige in der Karte)</label>
        <input id="printer_name" type="text" placeholder="Bambu Drucker">
      </div>
      <div class="row">
        <label>Währungssymbol</label>
        <input id="currency" type="text" placeholder="€">
      </div>`;

        // set current values
        const sel = this.shadowRoot.getElementById("serial");
        sel.value = c.serial ?? "";
        sel.addEventListener("change", e => { this._config = { ...this._config, serial: e.target.value }; this._fire(); });

        [["printer_name", ""], ["currency", "€"]].forEach(([id, def]) => {
            const inp = this.shadowRoot.getElementById(id);
            inp.value = c[id] ?? def;
            inp.addEventListener("change", e => { this._config = { ...this._config, [id]: e.target.value }; this._fire(); });
        });
    }
}


// ── Maintenance Card ──────────────────────────────────────────────────────────

class BambuCompanionMaintenanceCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: "open" });
        this._showAll = false; // default: only show warnings
    }

    setConfig(config) {
        this._config = config;
    }

    set hass(hass) { this._hass = hass; this._render(); }

    _render() {
        if (!this._hass || !this._config) return;
        if (!this._config.serial) {
            this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:var(--secondary-text-color)">Bitte einen Drucker in den Karteneinstellungen auswählen.</div></ha-card>`;
            return;
        }
        const h = this._hass;
        const { serial: _serial } = this._config;
        const serialLc = _serial.toLowerCase();

        // ── Find maintenance sensors via device registry ──────────────────
        // Uses the same device-registry approach as buildEntityMap() so that
        // entity IDs that HA auto-assigned (e.g. sensor.h2d_kermit_wartung_*)
        // are found regardless of their naming.
        let maintEntityIds = [];
        let selectEntityId = `select.bc_${serialLc}_maintenance_task`;
        let resetBtnId     = `button.bc_${serialLc}_reset_selected_task`;

        if (h.entities && h.devices) {
            // 1. Locate the bambu_companion device for this serial
            let targetDeviceId = null;
            for (const [did, device] of Object.entries(h.devices)) {
                for (const [domain, identifier] of (device.identifiers ?? [])) {
                    if (domain === "bambu_companion" && String(identifier).toLowerCase() === serialLc) {
                        targetDeviceId = did;
                        break;
                    }
                }
                if (targetDeviceId) break;
            }

            if (targetDeviceId) {
                // 2. Collect all bambu_companion entities for this device
                for (const [eid, entry] of Object.entries(h.entities)) {
                    if (entry.platform !== "bambu_companion") continue;
                    if (entry.device_id !== targetDeviceId) continue;
                    const state = h.states[eid];
                    if (!state) continue;
                    if (eid.startsWith("sensor.") && state.attributes.task_key !== undefined) {
                        maintEntityIds.push(eid);
                    } else if (eid.startsWith("select.") && !eid.includes("nozzle") && state.attributes.options !== undefined) {
                        // Maintenance task select (not the nozzle select)
                        selectEntityId = eid;
                    } else if (eid.startsWith("button.") && !eid.includes("nozzle")) {
                        // The reset_selected_task button (not a nozzle reset button)
                        resetBtnId = eid;
                    }
                }
            }
        }

        // ── Fallback: scan hass.states for sensors with task_key attribute ─
        if (!maintEntityIds.length) {
            const prefixFallback = `sensor.bc_${serialLc}_maint_`;
            for (const [eid, state] of Object.entries(h.states)) {
                if (!eid.startsWith("sensor.")) continue;
                if (state.attributes.task_key !== undefined) {
                    // If we have a serial hint, try to match it (skip unrelated printers)
                    const eidLc = eid.toLowerCase();
                    if (eidLc.startsWith(prefixFallback) || eidLc.includes(serialLc)) {
                        maintEntityIds.push(eid);
                    }
                }
            }
            // Last resort: all sensors with task_key (single-printer setups)
            if (!maintEntityIds.length) {
                for (const [eid, state] of Object.entries(h.states)) {
                    if (eid.startsWith("sensor.") && state.attributes.task_key !== undefined) {
                        maintEntityIds.push(eid);
                    }
                }
            }
        }

        const tasks = maintEntityIds
            .map(id => {
                const state = h.states[id];
                return {
                    id,
                    key: state.attributes.task_key ?? id,
                    name: state.attributes.task_name ?? (state.attributes.friendly_name ?? id).replace(/^.*\bWartung:\s*/i, ""),
                    status: state.state,
                    attrs: state.attributes,
                };
            })
            .sort((a, b) => (a.status === "warning" ? -1 : 1));

        console.debug(`BambuCompanion Maintenance [${serialLc}]: found ${tasks.length} tasks (${tasks.filter(t=>t.status==="warning").length} warnings), select="${selectEntityId}", btn="${resetBtnId}"`);

        const warnCount = tasks.filter(t => t.status === "warning").length;
        const visibleTasks = this._showAll ? tasks : tasks.filter(t => t.status === "warning");

        const rows = visibleTasks.map(t => {
            const warn = t.status === "warning";
            const trigger = t.attrs.trigger ?? "";
            const cur = t.attrs.current_value ?? 0;
            const itv = t.attrs.interval ?? 0;
            const fmt = (v) => (trigger === "print_count" || trigger === "laser_jobs")
                ? `${Math.round(v)} Drucke` : `${parseFloat(v).toFixed(1)} h`;
            const subText = warn
                ? `hat ${fmt(cur)} erreicht (Intervall: ${fmt(itv)})`
                : `${fmt(cur)} / ${fmt(itv)}`;
            return `
        <div class="task ${warn ? "warn" : "ok"}">
          <div class="task-left">
            <span class="task-icon">${warn ? "⚠️" : "✅"}</span>
            <div>
              <div class="task-name">${t.name}</div>
              <div class="task-sub ${warn ? "warning" : "muted"}">${subText}</div>
            </div>
          </div>
          ${warn ? `<button class="reset-btn" data-task-name="${t.name}" data-select="${selectEntityId}" data-button="${resetBtnId}">✅ Erledigt</button>` : ""}
        </div>`;
        }).join("");

        this.shadowRoot.innerHTML = `
      <style>
        ${SHARED_STYLE}
        .task {
          display: flex; align-items: center; justify-content: space-between;
          padding: 10px; border-radius: 8px; margin-bottom: 8px;
          background: var(--secondary-background-color);
        }
        .task.warn { border-left: 3px solid var(--warning-color, #ff9800); }
        .task.ok   { border-left: 3px solid var(--success-color, #4caf50); }
        .task-left { display: flex; align-items: center; gap: 10px; }
        .task-icon { font-size: 1.2em; }
        .task-name { font-weight: 500; font-size: 0.95em; }
        .task-sub  { font-size: 0.75em; }
        .reset-btn {
          background: var(--primary-color); color: white;
          border: none; border-radius: 4px; padding: 6px 12px;
          cursor: pointer; font-size: 0.82em; white-space: nowrap;
        }
        .reset-btn:hover { opacity: 0.85; }
        .toggle-btn {
          background: none; border: 1px solid var(--divider-color, #ccc);
          border-radius: 4px; padding: 3px 8px; cursor: pointer;
          font-size: 0.78em; color: var(--secondary-text-color);
        }
        .toggle-btn:hover { background: var(--secondary-background-color); }
        .card-header-row {
          display: flex; align-items: center; justify-content: space-between;
          padding: 12px 16px 0;
        }
        .card-header-title { font-size: 1.1em; font-weight: 500; }
        .empty { color: var(--secondary-text-color); text-align: center; padding: 20px; }
        .card-body { padding: 12px 16px; }
      </style>
      <ha-card>
        <div class="card-header-row">
          <span class="card-header-title">🔧 Nächste Wartungen${warnCount > 0 ? ` <span style="color:var(--warning-color,#ff9800);font-size:0.85em">(${warnCount} fällig)</span>` : ""}</span>
          <button class="toggle-btn" id="toggle-btn">${this._showAll ? "⚠️ Nur Warnungen" : `📋 Alle (${tasks.length})`}</button>
        </div>
        <div class="card-body">
          ${visibleTasks.length ? rows : `<div class="empty">${this._showAll ? "Keine Wartungsaufgaben gefunden" : "✅ Keine fälligen Wartungen"}</div>`}
        </div>
        <div style="padding:0 16px 8px;font-size:0.7em;color:var(--secondary-text-color);text-align:right">${tasks.length} Aufgaben (${warnCount} fällig)</div>
      </ha-card>
    `;

        this.shadowRoot.querySelector("#toggle-btn")?.addEventListener("click", () => {
            this._showAll = !this._showAll;
            this._render();
        });

        this.shadowRoot.querySelectorAll(".reset-btn").forEach(btn => {
            btn.addEventListener("click", async () => {
                const selectEid = btn.dataset.select;
                const buttonEid = btn.dataset.button;
                const taskName = btn.dataset.taskName;
                try {
                    await this._hass.callService("select", "select_option", { entity_id: selectEid, option: taskName });
                    await this._hass.callService("button", "press", { entity_id: buttonEid });
                } catch (e) {
                    console.error("BambuCompanion: Fehler beim Zurücksetzen:", e);
                }
            });
        });
    }

    getCardSize() { return 4; }
    getGridOptions() { return { columns: 12, rows: 4, min_columns: 6, min_rows: 3 }; }
    static getStubConfig() { return { serial: "" }; }
    static getConfigElement() { return document.createElement("bambu-companion-maintenance-card-editor"); }
}


// ── Maintenance Card Editor ───────────────────────────────────────────────────

class BambuCompanionMaintenanceCardEditor extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }); }

    setConfig(config) { this._config = config; this._render(); }
    set hass(hass) { this._hass = hass; this._render(); }

    _fire() {
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
    }

    _render() {
        if (!this._hass) return;
        const c = this._config || {};
        const printers = _findPrinters(this._hass);

        this.shadowRoot.innerHTML = `
      <style>${SHARED_EDITOR_STYLE}</style>
      <div class="row">
        <label>Drucker *</label>
        ${_printerSelect(printers, c.serial ?? "")}
      </div>`;

        const sel = this.shadowRoot.getElementById("serial");
        sel.value = c.serial ?? "";
        sel.addEventListener("change", e => { this._config = { ...this._config, serial: e.target.value }; this._fire(); });
    }
}


// ── History Card ──────────────────────────────────────────────────────────────

class BambuCompanionHistoryCard extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }); }

    setConfig(config) {
        this._config = config;
        this._entityMap = {};
    }

    set hass(hass) {
        this._hass = hass;
        if (this._config?.serial) {
            this._entityMap = buildEntityMap(hass, this._config.serial);
        }
        this._render();
    }

    _e(key) {
        return this._entityMap?.[key]
            ?? resolveEntityId(this._hass, `sensor.bc_${this._config.serial.toLowerCase()}_${key}`);
    }

    _render() {
        if (!this._hass || !this._config) return;
        if (!this._config.serial) {
            this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:var(--secondary-text-color)">Bitte einen Drucker in den Karteneinstellungen auswählen.</div></ha-card>`;
            return;
        }
        const h = this._hass;
        const { serial: _serial2, max_entries = 20, max_height = 400 } = this._config;
        const serial = _serial2.toLowerCase();

        // Read currency from sensor unit_of_measurement (set by integration config)
        const currencyEid = this._e("total_cost");
        const currency = h.states[currencyEid]?.attributes?.unit_of_measurement ?? "€";

        const totalPrintsEid = this._e("total_prints");
        const fullHistory = h.states[totalPrintsEid]?.attributes?.history ?? [];
        const history = max_entries > 0 ? fullHistory.slice(0, max_entries) : fullHistory;
        const scrollStyle = max_height > 0 ? `max-height:${max_height}px; overflow-y:auto;` : "overflow-y:auto;";

        const rows = history.map((p, idx) => {
            const ok = p.status === "success" || p.success === true;
            const ts = p.timestamp_end || p.end_time;
            const dateStr = ts
                ? (typeof ts === "number" ? new Date(ts * 1000) : new Date(ts)).toLocaleString()
                : "–";
            const duration = p.duration_min != null ? `${Math.round(p.duration_min)} min` : "–";
            const cost = p.total_cost != null ? `${parseFloat(p.total_cost).toFixed(2)} ${currency}` : "–";
            const fil = (p.filament_weight_g ?? p.total_filament_g) != null
                ? `${parseFloat(p.filament_weight_g ?? p.total_filament_g).toFixed(1)} g` : "–";
            const energy = p.energy_kwh != null ? `${parseFloat(p.energy_kwh).toFixed(3)} kWh` : "–";
            // Name: try all possible fields, last resort: extract from gcode_file path
            let printName = p.name || p.project_name || p.subtask_name || "";
            if (!printName && p.gcode_file) {
                // e.g. "ftp:///something/My_Print.gcode.3mf" → "My_Print.gcode"
                const fname = p.gcode_file.split("/").pop() || "";
                printName = fname.replace(/\.[^.]+$/, "").replace(/_/g, " ");
            }
            // Cover image: only use base64 data-URLs (saved at print-finish).
            // Old records without a saved image get a static placeholder — never
            // show the live entity_picture because that changes with every new print
            // and would make all history entries show the same current image.
            const stored = p.cover_image_url || "";
            const imgUrl = stored.startsWith("data:") ? stored : "";
            const thumbHtml = imgUrl
                ? `<img src="${imgUrl}" style="width:48px;height:48px;object-fit:cover;border-radius:4px;display:block;">`
                : `<div style="width:48px;height:48px;border-radius:4px;background:var(--divider-color);display:flex;align-items:center;justify-content:center;font-size:1.4em;">${ok ? "✅" : "❌"}</div>`;
            return `
        <tr class="print-row" data-idx="${idx}" style="cursor:pointer">
          <td style="width:56px;padding-right:4px">${thumbHtml}</td>
          <td>
            <div style="font-weight:500;font-size:0.9em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:140px">${printName || (ok ? "✅ Erfolgreich" : "❌ Fehlgeschlagen")}</div>
            <div class="muted" style="font-size:0.78em">${dateStr}</div>
          </td>
          <td class="right">${duration}</td>
          <td class="right">${fil}</td>
          <td class="right">${energy}</td>
          <td class="right">${cost}</td>
        </tr>`;
        }).join("");

        this.shadowRoot.innerHTML = `
      <style>
        ${SHARED_STYLE}
        .table-wrap { ${scrollStyle} }
        table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
        thead th {
          position: sticky; top: 0;
          background: var(--card-background-color);
          text-align: left; padding: 4px 6px;
          color: var(--secondary-text-color);
          font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.06em;
          z-index: 1;
        }
        td { padding: 8px 6px; border-top: 1px solid var(--divider-color); }
        .right { text-align: right; }
        .empty { color: var(--secondary-text-color); text-align: center; padding: 20px; }
        .print-row:hover td { background: var(--secondary-background-color); }
        /* ── Detail Modal ── */
        .modal-overlay {
          position: fixed; inset: 0; background: rgba(0,0,0,0.55);
          display: flex; align-items: center; justify-content: center;
          z-index: 9999; padding: 16px; box-sizing: border-box;
        }
        .modal {
          background: var(--card-background-color);
          border-radius: 12px; padding: 0; max-width: 480px; width: 100%;
          max-height: 90vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.35);
        }
        .modal-img { width: 100%; max-height: 200px; object-fit: cover; border-radius: 12px 12px 0 0; display: block; }
        .modal-img-placeholder {
          width: 100%; height: 120px; background: var(--secondary-background-color);
          border-radius: 12px 12px 0 0; display: flex; align-items: center;
          justify-content: center; font-size: 3em;
        }
        .modal-body { padding: 16px; }
        .modal-title { font-size: 1.05em; font-weight: 600; margin-bottom: 4px; }
        .modal-date { font-size: 0.78em; color: var(--secondary-text-color); margin-bottom: 12px; }
        .modal-badge {
          display: inline-block; font-size: 0.72em; font-weight: 700;
          padding: 2px 10px; border-radius: 10px; margin-bottom: 14px;
        }
        .badge-ok   { background: var(--success-color,#4caf50)22; color: var(--success-color,#4caf50); }
        .badge-fail { background: var(--error-color,#f44336)22;   color: var(--error-color,#f44336); }
        .modal-section { margin-bottom: 14px; }
        .modal-section-title {
          font-size: 0.7em; text-transform: uppercase; letter-spacing: 0.07em;
          color: var(--secondary-text-color); margin-bottom: 6px;
        }
        .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; }
        .detail-item label { font-size: 0.72em; color: var(--secondary-text-color); display: block; margin-bottom: 1px; }
        .detail-item span  { font-size: 0.88em; font-weight: 500; }
        .color-swatch {
          display: inline-block; width: 12px; height: 12px; border-radius: 50%;
          border: 1px solid var(--divider-color); vertical-align: middle; margin-right: 4px;
        }
        .close-btn {
          position: sticky; top: 0; float: right; margin: 10px 10px 0 0;
          background: var(--secondary-background-color); border: none;
          border-radius: 50%; width: 32px; height: 32px; cursor: pointer;
          font-size: 1.1em; color: var(--primary-text-color); z-index: 1;
          display: flex; align-items: center; justify-content: center;
        }
        .close-btn:hover { opacity: 0.75; }
      </style>
      <ha-card>
        <div class="card-header">📋 Druckverlauf</div>
        ${history.length ? `
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style="width:56px"></th>
                  <th>Name / Datum</th>
                  <th style="text-align:right">Dauer</th>
                  <th style="text-align:right">Filament</th>
                  <th style="text-align:right">Energie</th>
                  <th style="text-align:right">Kosten</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        ` : '<div class="empty">Noch keine Drucke aufgezeichnet</div>'}
      </ha-card>
    `;

        // Store history for detail popup
        this._historyData = history;
        this._currency = currency;

        // Single delegated click on table rows
        this.shadowRoot.querySelector("tbody")?.addEventListener("click", e => {
            const row = e.target.closest(".print-row");
            if (row) this._showDetail(parseInt(row.dataset.idx, 10));
        });
    }

    _showDetail(idx) {
        const p = this._historyData?.[idx];
        if (!p) return;
        const currency = this._currency ?? "€";
        const ok = p.status === "success" || p.success === true;

        let printName = p.name || p.project_name || p.subtask_name || "";
        if (!printName && p.gcode_file) {
            const fname = p.gcode_file.split("/").pop() || "";
            printName = fname.replace(/\.[^.]+$/, "").replace(/_/g, " ");
        }

        const ts = p.timestamp_end || p.end_time;
        const tsStart = p.timestamp_start || p.start_time;
        const dateEnd = ts ? (typeof ts === "number" ? new Date(ts * 1000) : new Date(ts)).toLocaleString() : "–";
        const dateStart = tsStart ? (typeof tsStart === "number" ? new Date(tsStart * 1000) : new Date(tsStart)).toLocaleString() : "–";

        const stored = p.cover_image_url || "";
        const imgUrl = stored.startsWith("data:") ? stored : "";
        const imgHtml = imgUrl
            ? `<img class="modal-img" src="${imgUrl}">`
            : `<div class="modal-img-placeholder">${ok ? "✅" : "❌"}</div>`;

        const tray = p.active_tray || {};
        const trayName = tray.name || "–";
        const trayType = tray.type || "–";
        const rawColor = tray.color || "";
        // Normalize color: strip leading # if present, treat as hex RRGGBB or RRGGBBAA
        const hexColor = rawColor.replace(/^#/, "").slice(0, 6);
        const colorStyle = hexColor ? `background:#${hexColor}` : "background:var(--divider-color)";
        const colorSwatch = `<span class="color-swatch" style="${colorStyle}"></span>`;
        const trayColor = hexColor ? `${colorSwatch}#${hexColor}` : "–";

        const amsIdx = tray.ams;
        const slotIdx = tray.slot;
        let source = "–";
        if (amsIdx != null && slotIdx != null) {
            source = `AMS ${parseInt(amsIdx) + 1}, Slot ${parseInt(slotIdx) + 1}`;
        } else if (amsIdx != null) {
            source = `AMS ${parseInt(amsIdx) + 1}`;
        } else if (slotIdx != null) {
            source = `Extern (Slot ${parseInt(slotIdx) + 1})`;
        } else if (trayName && trayName !== "–") {
            source = "Extern";
        }

        const nozzleDia = p.nozzle_diameter != null ? `${p.nozzle_diameter} mm` : "–";
        const nozzleType = p.nozzle_type || "–";
        const nozzleTemp = p.avg_nozzle_temp ? `${Math.round(p.avg_nozzle_temp)} °C` : "–";
        const bedType = p.bed_type || "–";
        const bedTemp = p.avg_bed_temp ? `${Math.round(p.avg_bed_temp)} °C` : "–";
        const layers = (p.layer_count > 0)
            ? (ok ? `${p.layer_count}` : `${p.current_layer || "?"} / ${p.layer_count}`)
            : "–";
        const progress = p.progress_at_end != null ? `${p.progress_at_end} %` : "–";
        const duration = p.duration_min != null ? `${Math.round(p.duration_min)} min` : "–";
        const filWeight = p.filament_weight_g != null ? `${parseFloat(p.filament_weight_g).toFixed(1)} g` : "–";
        const filCost = p.filament_cost != null ? `${parseFloat(p.filament_cost).toFixed(2)} ${currency}` : "–";
        const energyKwh = p.energy_kwh != null ? `${parseFloat(p.energy_kwh).toFixed(3)} kWh` : "–";
        const energyCost = p.energy_cost != null ? `${parseFloat(p.energy_cost).toFixed(2)} ${currency}` : "–";
        const totalCost = p.total_cost != null ? `${parseFloat(p.total_cost).toFixed(2)} ${currency}` : "–";
        const plate = p.plate || "–";

        const row2 = (label1, val1, label2, val2) => `
          <div class="detail-item"><label>${label1}</label><span>${val1}</span></div>
          <div class="detail-item"><label>${label2}</label><span>${val2}</span></div>`;

        const overlay = document.createElement("div");
        overlay.className = "modal-overlay";
        overlay.innerHTML = `
          <div class="modal">
            <button class="close-btn" id="close-modal">✕</button>
            ${imgHtml}
            <div class="modal-body">
              <div class="modal-title">${printName || (ok ? "Erfolgreicher Druck" : "Fehlgeschlagener Druck")}</div>
              <div class="modal-date">Beendet: ${dateEnd}</div>
              <span class="modal-badge ${ok ? "badge-ok" : "badge-fail"}">${ok ? "✅ Erfolgreich" : "❌ Fehlgeschlagen"} – ${progress}</span>

              <div class="modal-section">
                <div class="modal-section-title">🧵 Filament</div>
                <div class="detail-grid">
                  ${row2("Material", trayName, "Typ", trayType)}
                  ${row2("Farbe", trayColor, "Lager", source)}
                  ${row2("Verbrauch", filWeight, "Kosten", filCost)}
                </div>
              </div>

              <div class="modal-section">
                <div class="modal-section-title">🔧 Düse & Bett</div>
                <div class="detail-grid">
                  ${row2("Düse", nozzleDia, "Typ", nozzleType)}
                  ${row2("Düsentemp.", nozzleTemp, "Betttyp", bedType)}
                  ${row2("Betttemp.", bedTemp, "Platte", plate)}
                </div>
              </div>

              <div class="modal-section">
                <div class="modal-section-title">📊 Druckdetails</div>
                <div class="detail-grid">
                  ${row2("Dauer", duration, "Schichten", layers)}
                  ${row2("Gestartet", dateStart, "Beendet", dateEnd)}
                </div>
              </div>

              <div class="modal-section">
                <div class="modal-section-title">⚡ Energie & Kosten</div>
                <div class="detail-grid">
                  ${row2("Energie", energyKwh, "Energiekosten", energyCost)}
                  ${row2("Filamentkosten", filCost, "Gesamt", totalCost)}
                </div>
              </div>
            </div>
          </div>`;

        overlay.addEventListener("click", e => { if (e.target === overlay) overlay.remove(); });
        overlay.querySelector("#close-modal").addEventListener("click", () => overlay.remove());
        this.shadowRoot.appendChild(overlay);
    }

    getCardSize() { return 5; }
    getGridOptions() { return { columns: 12, rows: 8, min_columns: 6, min_rows: 4 }; }
    static getStubConfig() { return { serial: "", max_entries: 20, max_height: 400 }; }
    static getConfigElement() { return document.createElement("bambu-companion-history-card-editor"); }
}


// ── History Card Editor ───────────────────────────────────────────────────────

class BambuCompanionHistoryCardEditor extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }); }

    setConfig(config) { this._config = config; this._render(); }
    set hass(hass) { this._hass = hass; this._render(); }

    _fire() {
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
    }

    _render() {
        if (!this._hass) return;
        const c = this._config || {};
        const printers = _findPrinters(this._hass);

        this.shadowRoot.innerHTML = `
      <style>${SHARED_EDITOR_STYLE}</style>
      <div class="row">
        <label>Drucker *</label>
        ${_printerSelect(printers, c.serial ?? "")}
      </div>
      <div class="row">
        <label>Anzahl Einträge (0 = alle anzeigen)</label>
        <input id="max_entries" type="number" min="0" step="5" placeholder="20">
      </div>
      <div class="row">
        <label>Maximale Höhe in px (0 = unbegrenzt)</label>
        <input id="max_height" type="number" min="0" step="50" placeholder="400">
      </div>`;

        const sel = this.shadowRoot.getElementById("serial");
        sel.value = c.serial ?? "";
        sel.addEventListener("change", e => { this._config = { ...this._config, serial: e.target.value }; this._fire(); });

        const inp = this.shadowRoot.getElementById("max_entries");
        inp.value = c.max_entries ?? 20;
        inp.addEventListener("change", e => {
            this._config = { ...this._config, max_entries: parseInt(e.target.value, 10) || 0 };
            this._fire();
        });

        const inpH = this.shadowRoot.getElementById("max_height");
        inpH.value = c.max_height ?? 400;
        inpH.addEventListener("change", e => {
            this._config = { ...this._config, max_height: parseInt(e.target.value, 10) || 0 };
            this._fire();
        });
    }
}


// ── Register ──────────────────────────────────────────────────────────────────

customElements.define("bambu-companion-overview-card", BambuCompanionOverviewCard);
customElements.define("bambu-companion-overview-card-editor", BambuCompanionOverviewCardEditor);
customElements.define("bambu-companion-maintenance-card", BambuCompanionMaintenanceCard);
customElements.define("bambu-companion-maintenance-card-editor", BambuCompanionMaintenanceCardEditor);
customElements.define("bambu-companion-history-card", BambuCompanionHistoryCard);
customElements.define("bambu-companion-history-card-editor", BambuCompanionHistoryCardEditor);

window.customCards = window.customCards || [];
window.customCards.push(
    {
        type: "bambu-companion-overview-card",
        name: "Bambu Companion – Übersicht",
        description: "Druckstatistiken (Zähler, Kosten, Energie) für einen Bambu-Drucker",
        preview: true,
    },
    {
        type: "bambu-companion-maintenance-card",
        name: "Bambu Companion – Wartung",
        description: "Wartungsstatus aller Aufgaben mit Reset-Buttons",
        preview: true,
    },
    {
        type: "bambu-companion-history-card",
        name: "Bambu Companion – Druckverlauf",
        description: "Tabelle der letzten Drucke mit Dauer, Filament und Kosten",
        preview: true,
    }
);

console.info(
    `%c BAMBU-COMPANION-CARDS %c v${VERSION} `,
    "color:#fff;background:#03a9f4;font-weight:bold;padding:2px 4px;border-radius:3px 0 0 3px",
    "color:#03a9f4;font-weight:bold;padding:2px 4px;border:1px solid #03a9f4;border-radius:0 3px 3px 0"
);
