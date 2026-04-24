/**
 * Bambu Companion Cards for Home Assistant
 * Three custom Lovelace cards:
 *   bambu-companion-overview-card
 *   bambu-companion-maintenance-card
 *   bambu-companion-history-card
 */
const VERSION = "1.0.0";

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


// ── Overview Card ─────────────────────────────────────────────────────────────

class BambuCompanionOverviewCard extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }); }

    setConfig(config) {
        if (!config.serial) throw new Error("Bambu Companion Overview: 'serial' is required");
        this._config = config;
    }

    set hass(hass) { this._hass = hass; this._render(); }

    _e(key) { return `sensor.bc_${this._config.serial}_${key}`; }

    _render() {
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
}


// ── Maintenance Card ──────────────────────────────────────────────────────────

class BambuCompanionMaintenanceCard extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }); }

    setConfig(config) {
        if (!config.serial) throw new Error("Bambu Companion Maintenance: 'serial' is required");
        this._config = config;
    }

    set hass(hass) { this._hass = hass; this._render(); }

    _render() {
        if (!this._hass || !this._config) return;
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
}


// ── History Card ──────────────────────────────────────────────────────────────

class BambuCompanionHistoryCard extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }); }

    setConfig(config) {
        if (!config.serial) throw new Error("Bambu Companion History: 'serial' is required");
        this._config = config;
    }

    set hass(hass) { this._hass = hass; this._render(); }

    _render() {
        if (!this._hass || !this._config) return;
        const h = this._hass;
        const { serial, currency = "€", max_items = 10 } = this._config;

        const entityId = `sensor.bc_${serial}_total_prints`;
        const history = (h.states[entityId]?.attributes?.history ?? []).slice(0, max_items);

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
        table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
        th {
          text-align: left; padding: 4px 6px;
          color: var(--secondary-text-color);
          font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.06em;
        }
        td { padding: 8px 6px; border-top: 1px solid var(--divider-color); }
        .right { text-align: right; }
        .empty { color: var(--secondary-text-color); text-align: center; padding: 20px; }
      </style>
      <ha-card>
        <div class="card-header">📋 Druckverlauf</div>
        ${history.length ? `
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
        ` : '<div class="empty">Noch keine Drucke aufgezeichnet</div>'}
      </ha-card>
    `;
    }

    getCardSize() { return 5; }
    static getStubConfig() { return { serial: "", currency: "€", max_items: 10 }; }
}


// ── Register ──────────────────────────────────────────────────────────────────

customElements.define("bambu-companion-overview-card", BambuCompanionOverviewCard);
customElements.define("bambu-companion-maintenance-card", BambuCompanionMaintenanceCard);
customElements.define("bambu-companion-history-card", BambuCompanionHistoryCard);

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
