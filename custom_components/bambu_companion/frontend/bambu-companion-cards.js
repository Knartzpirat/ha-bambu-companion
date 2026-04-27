/**
 * Bambu Companion Cards for Home Assistant
 * Three custom Lovelace cards:
 *   bambu-companion-overview-card
 *   bambu-companion-maintenance-card
 *   bambu-companion-history-card
 */
const VERSION = "1.3.4";

// ── Helpers ────────────────────────────────────────────────────────────────────

function getState(hass, entityId) {
    return hass.states[entityId]?.state ?? "unavailable";
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
  :host { display: block; }
  ha-card { padding: 16px; box-sizing: border-box; }
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
    const seen = new Set();

    // Method 1 (most reliable): scan device registry for devices owned by bambu_companion.
    // Every install has a device with identifiers = [["bambu_companion", serial]].
    if (hass.devices) {
        for (const device of Object.values(hass.devices)) {
            for (const [domain, identifier] of (device.identifiers ?? [])) {
                if (domain !== "bambu_companion" || seen.has(identifier)) continue;
                seen.add(identifier);
                result.push({
                    serial: identifier,
                    label: device.name_by_user || device.name || identifier,
                });
            }
        }
    }

    // Method 2: scan hass.states for bc_ entity_id pattern (new installs, or when devices not populated)
    for (const entityId of Object.keys(hass.states ?? {})) {
        const m = entityId.match(/^sensor\.bc_(.+?)_print_status$/i);
        if (!m || seen.has(m[1])) continue;
        seen.add(m[1]);
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
    }

    set hass(hass) { this._hass = hass; this._render(); }

    _e(key) { return `sensor.bc_${this._config.serial}_${key}`; }

    _render() {
        if (!this._config?.serial) {
            this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:var(--secondary-text-color)">Bitte einen Drucker in den Karteneinstellungen auswählen.</div></ha-card>`;
            return;
        }
        if (!this._hass || !this._config) return;
        const h = this._hass;
        const { serial, currency = "€", printer_name = serial } = this._config;

        const status = getState(h, this._e("print_status"));
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
      </style>
      <ha-card>
        <div class="card-header">
          <div class="status-dot"></div>
          <span>📊 ${printer_name}</span>
          <div class="status-badge">${status}${isPrinting ? ` ${progress}%` : ""}</div>
        </div>

        ${isPrinting ? `<div class="progress-bar"><div class="progress-fill"></div></div>` : ""}

        <section>
          <div class="section-label">Drucke</div>
          <div class="grid-3">
            <div class="tile"><div class="tile-value">${totalPrints}</div><div class="tile-label">Gesamt</div></div>
            <div class="tile"><div class="tile-value ok">${successPrints}</div><div class="tile-label">Erfolgreich</div></div>
            <div class="tile"><div class="tile-value error">${failedPrints}</div><div class="tile-label">Fehlgeschlagen</div></div>
          </div>
        </section>

        <section>
          <div class="section-label">Verbrauch gesamt</div>
          <div class="grid-3">
            <div class="tile"><div class="tile-value">${printTime.toFixed(1)} h</div><div class="tile-label">Druckzeit</div></div>
            <div class="tile"><div class="tile-value">${filament.toFixed(0)} g</div><div class="tile-label">Filament</div></div>
            <div class="tile"><div class="tile-value">${energy.toFixed(2)} kWh</div><div class="tile-label">Energie</div></div>
          </div>
        </section>

        <hr>

        <section>
          <div class="section-label">Diesen Monat</div>
          <div class="grid-2">
            <div class="tile"><div class="tile-value">${monthlyPrints}</div><div class="tile-label">Drucke</div></div>
            <div class="tile"><div class="tile-value">${monthlyCost.toFixed(2)} ${currency}</div><div class="tile-label">Kosten</div></div>
          </div>
        </section>

        <section>
          <div class="section-label">Letzter Druck</div>
          <div class="grid-2">
            <div class="tile"><div class="tile-value">${lastDuration} min</div><div class="tile-label">Dauer</div></div>
            <div class="tile"><div class="tile-value">${lastCost.toFixed(2)} ${currency}</div><div class="tile-label">Kosten</div></div>
          </div>
        </section>

        <div class="tile" style="text-align:center">
          <div class="tile-value">${totalCost.toFixed(2)} ${currency}</div>
          <div class="tile-label">Gesamtkosten</div>
        </div>
      </ha-card>
    `;
    }

    getCardSize() { return 7; }
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
    constructor() { super(); this.attachShadow({ mode: "open" }); }

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
        const { serial } = this._config;
        const prefix = `sensor.bc_${serial}_maint_`;

        const tasks = Object.entries(h.states)
            .filter(([id]) => id.startsWith(prefix))
            .map(([id, state]) => ({
                key: id.slice(prefix.length),
                name: (state.attributes.friendly_name ?? id).replace(/^Wartung:\s*/i, ""),
                status: state.state,
                attrs: state.attributes,
            }))
            .sort((a, b) => (a.status === "warning" ? -1 : 1));

        const rows = tasks.map(t => {
            const warn = t.status === "warning";
            const btnId = `button.bc_${serial}_reset_maint_${t.key}`;
            return `
        <div class="task ${warn ? "warn" : "ok"}">
          <div class="task-left">
            <span class="task-icon">${warn ? "⚠️" : "✅"}</span>
            <div>
              <div class="task-name">${t.name}</div>
              <div class="task-sub ${warn ? "warning" : "muted"}">${warn ? "Wartung fällig" : "In Ordnung"}</div>
            </div>
          </div>
          <button class="reset-btn" data-entity="${btnId}">Erledigt</button>
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
        .empty { color: var(--secondary-text-color); text-align: center; padding: 20px; }
      </style>
      <ha-card>
        <div class="card-header">🔧 Nächste Wartungen</div>
        ${tasks.length ? rows : '<div class="empty">Keine Wartungsaufgaben gefunden</div>'}
      </ha-card>
    `;

        this.shadowRoot.querySelectorAll(".reset-btn").forEach(btn => {
            btn.addEventListener("click", () =>
                this._hass.callService("button", "press", { entity_id: btn.dataset.entity })
            );
        });
    }

    getCardSize() { return 4; }
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
    }

    set hass(hass) { this._hass = hass; this._render(); }

    _render() {
        if (!this._hass || !this._config) return;
        if (!this._config.serial) {
            this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:var(--secondary-text-color)">Bitte einen Drucker in den Karteneinstellungen auswählen.</div></ha-card>`;
            return;
        }
        const h = this._hass;
        const { serial, max_entries = 20, max_height = 400 } = this._config;

        // Read currency from sensor unit_of_measurement (set by integration config)
        const currency = h.states[`sensor.bc_${serial}_total_cost`]?.attributes?.unit_of_measurement ?? "€";

        const entityId = `sensor.bc_${serial}_total_prints`;
        const fullHistory = h.states[entityId]?.attributes?.history ?? [];
        const history = max_entries > 0 ? fullHistory.slice(0, max_entries) : fullHistory;
        const scrollStyle = max_height > 0 ? `max-height:${max_height}px; overflow-y:auto;` : "overflow-y:auto;";

        const rows = history.map(p => {
            const ok = p.success !== false;
            const dateStr = p.end_time ? new Date(p.end_time * 1000).toLocaleString() : "–";
            const duration = p.duration_min != null ? `${Math.round(p.duration_min)} min` : "–";
            const cost = p.total_cost != null ? `${parseFloat(p.total_cost).toFixed(2)} ${currency}` : "–";
            const fil = p.total_filament_g != null ? `${parseFloat(p.total_filament_g).toFixed(1)} g` : "–";
            return `
        <tr>
          <td>${ok ? "✅" : "❌"}</td>
          <td class="muted">${dateStr}</td>
          <td class="right">${duration}</td>
          <td class="right">${fil}</td>
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
      </style>
      <ha-card>
        <div class="card-header">📋 Druckverlauf</div>
        ${history.length ? `
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>Datum</th>
                  <th style="text-align:right">Dauer</th>
                  <th style="text-align:right">Filament</th>
                  <th style="text-align:right">Kosten</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        ` : '<div class="empty">Noch keine Drucke aufgezeichnet</div>'}
      </ha-card>
    `;
    }

    getCardSize() { return 5; }
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
