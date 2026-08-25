const HEAT_SOURCES = {
  ashp: "Air source heat pump (ASHP)",
  modulating_boiler: "Modulating / condensing boiler",
  non_condensing_boiler: "Older non-condensing boiler",
  other: "Other / not sure",
};

const HEAT_SOURCE_DELAYS = {
  ashp: 300,
  modulating_boiler: 120,
  non_condensing_boiler: 60,
  other: 300,
};

const COMPETING_SCHEDULER_WARNING =
  "Do not assign a thermostat to more than one thermostat setpoint scheduler. " +
  "If ZEAL and another integration, automation, blueprint or schedule both change " +
  "the same thermostat’s target temperature, they may repeatedly overwrite each " +
  "other. Before enabling ZEAL scheduling, disable any other setpoint scheduler " +
  "controlling those thermostat entities.";

class ZealPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._started = false;
    this._view = "overview";
    this._entries = [];
    this._entryId = null;
    this._configuration = null;
    this._draft = [];
    this._loading = true;
    this._saving = false;
    this._dirty = false;
    this._notice = "";
    this._error = "";
  }

  set hass(value) {
    this._hass = value;
    if (!this._started && value) {
      this._started = true;
      this._initialLoad();
    }
  }

  set narrow(_value) {}
  set route(_value) {}
  set panel(_value) {}

  connectedCallback() {
    this._render();
  }

  async _initialLoad() {
    this._loading = true;
    this._render();
    try {
      const response = await this._hass.callWS({ type: "zeal/list_entries" });
      this._entries = response.entries || [];
      if (!this._entries.length) {
        this._loading = false;
        this._error = "No loaded ZEAL instance was found.";
        this._render();
        return;
      }
      this._entryId = this._entries[0].entry_id;
      await this._loadConfiguration();
    } catch (error) {
      this._loading = false;
      this._error = this._message(error, "ZEAL could not be loaded.");
      this._render();
    }
  }

  async _loadConfiguration({ preserveNotice = false } = {}) {
    if (!this._entryId) return;
    this._loading = true;
    this._error = "";
    if (!preserveNotice) this._notice = "";
    this._render();
    try {
      const configuration = await this._hass.callWS({
        type: "zeal/get_configuration",
        entry_id: this._entryId,
      });
      this._acceptConfiguration(configuration);
    } catch (error) {
      this._loading = false;
      this._error = this._message(error, "ZEAL configuration could not be loaded.");
      this._render();
    }
  }

  _acceptConfiguration(configuration) {
    this._configuration = configuration;
    this._draft = this._copy(configuration.zones || []);
    this._dirty = false;
    this._loading = false;
    this._error = "";
    this._render();
  }

  _copy(value) {
    return JSON.parse(JSON.stringify(value));
  }

  _message(error, fallback) {
    return error && (error.message || error.body?.message)
      ? error.message || error.body.message
      : fallback;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _entityLabel(entity) {
    if (!entity) return "Not selected";
    const name = entity.name && entity.name !== entity.entity_id ? entity.name : "";
    return name ? `${name} · ${entity.entity_id}` : entity.entity_id;
  }

  _areaName(areaId) {
    const area = this._configuration?.catalog?.areas?.find(
      (candidate) => candidate.area_id === areaId
    );
    return area?.name || areaId;
  }

  _zealThermostat(roomId) {
    return (this._configuration?.catalog?.zeal_room_thermostats || []).find(
      (thermostat) => thermostat.room_id === roomId
    );
  }

  _render() {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `${this._styles()}<main>${this._content()}</main>`;
    this._bindEvents();
  }

  _content() {
    if (this._loading) {
      return `<div class="center-state"><div class="spinner"></div><p>Loading ZEAL…</p></div>`;
    }
    if (!this._configuration) {
      return `<div class="shell"><section class="message error">${this._escape(
        this._error || "ZEAL is not available."
      )}</section><button class="primary" data-action="reload-all">Try again</button></div>`;
    }
    return `
      <div class="shell">
        ${this._header()}
        ${this._messages()}
        ${this._view === "setup" ? this._renderSetup() : this._renderOverview()}
      </div>`;
  }

  _header() {
    const entrySelector =
      this._entries.length > 1
        ? `<label class="entry-picker">ZEAL instance
            <select data-action="select-entry">${this._entries
              .map(
                (entry) =>
                  `<option value="${this._escape(entry.entry_id)}" ${
                    entry.entry_id === this._entryId ? "selected" : ""
                  }>${this._escape(entry.title)}</option>`
              )
              .join("")}</select>
          </label>`
        : "";
    return `
      <header>
        <div class="identity">
          <img src="/api/brands/integration/zeal/icon.png" alt="" />
          <div><h1>ZEAL</h1><p>Zone Energy-Aware Logic</p></div>
        </div>
        ${entrySelector}
      </header>
      <nav aria-label="ZEAL sections">
        <button class="tab ${this._view === "overview" ? "active" : ""}" data-view="overview">Overview</button>
        <button class="tab ${this._view === "setup" ? "active" : ""}" data-view="setup">Setup</button>
      </nav>`;
  }

  _messages() {
    return `${
      this._notice
        ? `<section class="message success" role="status">${this._escape(this._notice)}</section>`
        : ""
    }${
      this._error
        ? `<section class="message error" role="alert">${this._escape(this._error)}</section>`
        : ""
    }`;
  }

  _warning() {
    return `<aside class="safety-warning"><span class="warning-icon">!</span><div><strong>Prevent competing setpoint control</strong><p>${this._escape(
      COMPETING_SCHEDULER_WARNING
    )}</p></div></aside>`;
  }

  _renderOverview() {
    const zones = this._configuration.zones || [];
    const rooms = zones.flatMap((zone) => zone.rooms || []);
    const activeRooms = rooms.filter((room) => room.active !== false).length;
    const trvs = rooms.reduce((total, room) => total + (room.trvs || []).length, 0);
    return `
      <section class="page-heading">
        <div><h2>System overview</h2><p>Heating zones and the Home Assistant equipment ZEAL controls.</p></div>
        <button class="primary" data-view="setup">${zones.length ? "Modify setup" : "Start setup"}</button>
      </section>
      ${this._warning()}
      <section class="summary-grid" aria-label="Configuration summary">
        ${this._summaryCard("Heating zones", zones.length, "mdi:radiator")}
        ${this._summaryCard("Active rooms", activeRooms, "mdi:home-thermometer")}
        ${this._summaryCard("Physical TRVs", trvs, "mdi:thermostat")}
      </section>
      ${
        zones.length
          ? `<section class="zone-grid">${zones
              .map((zone) => this._overviewZone(zone))
              .join("")}</section>`
          : `<section class="empty-card"><h3>No heating zones yet</h3><p>Use Setup to connect Home Assistant Areas, thermostatic valves, temperature sensors and a heating actuator.</p><button class="primary" data-view="setup">Configure ZEAL</button></section>`
      }`;
  }

  _summaryCard(label, value, icon) {
    return `<article class="summary-card"><ha-icon icon="${icon}"></ha-icon><div><strong>${value}</strong><span>${label}</span></div></article>`;
  }

  _overviewZone(zone) {
    const switchEntity = this._configuration.catalog.switches.find(
      (item) => item.entity_id === zone.switch
    );
    return `<article class="zone-card">
      <div class="zone-title"><div><h3>${this._escape(zone.name)}</h3><p>${this._escape(
        HEAT_SOURCES[zone.heat_source] || zone.heat_source
      )}</p></div><span class="pill">${(zone.rooms || []).length} room${
        (zone.rooms || []).length === 1 ? "" : "s"
      }</span></div>
      <dl class="zone-facts">
        <div><dt>Heating actuator</dt><dd>${this._escape(
          this._entityLabel(switchEntity)
        )}</dd></div>
        <div><dt>Re-enable delay</dt><dd>${Number(zone.reenable_delay ?? 300)} seconds</dd></div>
      </dl>
      <div class="room-list">${
        (zone.rooms || []).length
          ? zone.rooms.map((room) => this._overviewRoom(room)).join("")
          : `<p class="muted">No Areas assigned to this zone.</p>`
      }</div>
    </article>`;
  }

  _overviewRoom(room) {
    const zealThermostat = this._zealThermostat(room.room_id);
    return `<div class="room-summary">
      <div><strong>${this._escape(room.name || this._areaName(room.room_id))}</strong><span>${this._escape(
        this._areaName(room.room_id)
      )} · ${(room.trvs || []).length} TRV${(room.trvs || []).length === 1 ? "" : "s"} · ${
        (room.sensors || []).length
      } sensor${(room.sensors || []).length === 1 ? "" : "s"}</span><span>ZEAL target: ${this._escape(
        zealThermostat ? this._entityLabel(zealThermostat) : "Not created"
      )}</span></div>
      <span class="state ${room.active === false ? "inactive" : ""}">${
        room.active === false ? "Inactive" : "Active"
      }</span>
    </div>`;
  }

  _renderSetup() {
    const usedAreas = new Set(
      this._draft.flatMap((zone) => (zone.rooms || []).map((room) => room.room_id))
    );
    const unassignedAreas = (this._configuration.catalog.areas || []).filter(
      (area) => !usedAreas.has(area.area_id)
    );
    return `
      <section class="page-heading">
        <div><h2>Setup</h2><p>Build each heating zone from Home Assistant Areas and their equipment.</p></div>
        <button class="secondary" data-action="add-zone">+ Add zone</button>
      </section>
      ${this._warning()}
      <section class="setup-help">
        <strong>Before you begin</strong>
        <p>Create and assign your Areas, physical climate entities, temperature sensors and actuator switches in Home Assistant first. An Area can belong to one ZEAL zone only.</p>
      </section>
      <section class="setup-zones">
        ${
          this._draft.length
            ? this._draft
                .map((zone, zoneIndex) =>
                  this._setupZone(zone, zoneIndex, unassignedAreas)
                )
                .join("")
            : `<div class="empty-card"><h3>Add your first heating zone</h3><p>A zone normally represents a floor, heating circuit or other group sharing one heating actuator.</p><button class="primary" data-action="add-zone">+ Add zone</button></div>`
        }
      </section>
      <div class="save-bar">
        <span class="save-state">${this._dirty ? "Unsaved setup changes" : "Setup is up to date"}</span>
        <div><button class="text-button" data-action="reset" ${
          !this._dirty || this._saving ? "disabled" : ""
        }>Discard changes</button><button class="primary" data-action="save" ${
          !this._dirty || this._saving ? "disabled" : ""
        }>${this._saving ? "Saving…" : "Save setup"}</button></div>
      </div>`;
  }

  _setupZone(zone, zoneIndex, unassignedAreas) {
    const selectedSwitches = new Set(
      this._draft
        .filter((_candidate, index) => index !== zoneIndex)
        .map((candidate) => candidate.switch)
        .filter(Boolean)
    );
    const switchOptions = (this._configuration.catalog.switches || []).filter(
      (item) => !selectedSwitches.has(item.entity_id) || item.entity_id === zone.switch
    );
    return `<article class="setup-zone">
      <div class="setup-zone-title"><h3>Zone ${zoneIndex + 1}</h3><button class="danger-link" data-action="remove-zone" data-zone="${zoneIndex}">Remove zone</button></div>
      <div class="form-grid">
        <label>Zone name<input data-zone="${zoneIndex}" data-zone-field="name" value="${this._escape(
          zone.name
        )}" placeholder="e.g. Ground Floor" /></label>
        <label>Heating actuator switch<select data-zone="${zoneIndex}" data-zone-field="switch">
          <option value="">Not selected</option>${switchOptions
            .map(
              (item) =>
                `<option value="${this._escape(item.entity_id)}" ${
                  item.entity_id === zone.switch ? "selected" : ""
                }>${this._escape(this._entityLabel(item))}</option>`
            )
            .join("")}
        </select></label>
        <label>Heat source<select data-zone="${zoneIndex}" data-zone-field="heat_source">
          ${Object.entries(HEAT_SOURCES)
            .map(
              ([value, label]) =>
                `<option value="${value}" ${zone.heat_source === value ? "selected" : ""}>${this._escape(
                  label
                )}</option>`
            )
            .join("")}
        </select><small>Suggested delay: ${HEAT_SOURCE_DELAYS[zone.heat_source] ?? 300} seconds.</small></label>
        <label>Re-enable delay (seconds)<input type="number" min="0" max="3600" step="15" data-zone="${zoneIndex}" data-zone-field="reenable_delay" value="${Number(
          zone.reenable_delay ?? 300
        )}" /><small>Minimum off time before this zone may turn on again.</small></label>
      </div>
      <div class="rooms-heading"><div><h4>Rooms</h4><p>Each room is a Home Assistant Area.</p></div>
        <select class="add-room" data-action="add-room" data-zone="${zoneIndex}" ${
          unassignedAreas.length ? "" : "disabled"
        }><option value="">${unassignedAreas.length ? "+ Add Area as room" : "All Areas are assigned"}</option>${unassignedAreas
          .map(
            (area) =>
              `<option value="${this._escape(area.area_id)}">${this._escape(area.name)}</option>`
          )
          .join("")}</select>
      </div>
      ${this._zoneThermostatBoundary(zone)}
      <div class="room-editors">${
        (zone.rooms || []).length
          ? zone.rooms
              .map((room, roomIndex) => this._setupRoom(room, zoneIndex, roomIndex))
              .join("")
          : `<div class="room-empty">No Areas assigned. Choose an Area above.</div>`
      }</div>
    </article>`;
  }

  _zoneThermostatBoundary(zone) {
    const targets = (zone.rooms || [])
      .map((room) => ({ room, thermostat: this._zealThermostat(room.room_id) }))
      .filter(({ thermostat }) => thermostat);
    return `<aside class="control-boundary">
      <div><strong>Zone/Floor scheduling targets</strong><p>ZEAL schedules only its own canonical room thermostats. These are created automatically and cannot be selected as physical room equipment.</p></div>
      ${
        targets.length
          ? `<ul>${targets
              .map(
                ({ room, thermostat }) =>
                  `<li><span>${this._escape(room.name || this._areaName(room.room_id))}</span><code>${this._escape(
                    thermostat.entity_id
                  )}</code></li>`
              )
              .join("")}</ul>`
          : `<p class="muted">ZEAL room thermostats appear here after rooms with physical thermostats are saved.</p>`
      }
    </aside>`;
  }

  _setupRoom(room, zoneIndex, roomIndex) {
    const trvs = (this._configuration.catalog.physical_room_thermostats || []).filter(
      (item) => item.area_id === room.room_id
    );
    const sensors = (this._configuration.catalog.temperature_sensors || []).filter(
      (item) => item.area_id === room.room_id
    );
    const zealThermostat = this._zealThermostat(room.room_id);
    return `<section class="room-editor">
      <div class="room-editor-title"><div><h4>${this._escape(
        this._areaName(room.room_id)
      )}</h4><p>Home Assistant Area</p></div><button class="danger-link" data-action="remove-room" data-zone="${zoneIndex}" data-room="${roomIndex}">Remove</button></div>
      <label class="active-toggle"><input type="checkbox" data-zone="${zoneIndex}" data-room="${roomIndex}" data-room-field="active" ${
        room.active === false ? "" : "checked"
      } /><span><strong>Room is active</strong><small>Inactive rooms do not request heat.</small></span></label>
      <div class="canonical-target"><ha-icon icon="mdi:thermostat"></ha-icon><div><strong>ZEAL room thermostat</strong><span>${this._escape(
        zealThermostat
          ? this._entityLabel(zealThermostat)
          : "Created automatically after this room is saved with a physical thermostat"
      )}</span><small>This is the room's canonical scheduling target. It is never offered below as a physical thermostat.</small></div></div>
      <div class="equipment-grid">
        ${this._multiSelect(
          "Physical room thermostats / TRVs",
          trvs,
          room.trvs || [],
          zoneIndex,
          roomIndex,
          "trvs",
          "Choose every physical climate entity in this Area that ZEAL should control."
        )}
        ${this._multiSelect(
          "Temperature sensors",
          sensors,
          room.sensors || [],
          zoneIndex,
          roomIndex,
          "sensors",
          "Choose the Area sensors ZEAL should use to measure room temperature."
        )}
      </div>
    </section>`;
  }

  _multiSelect(label, items, selected, zoneIndex, roomIndex, field, help) {
    const selectedSet = new Set(selected);
    return `<label>${label}<select multiple size="${Math.max(2, Math.min(5, items.length || 2))}" data-zone="${zoneIndex}" data-room="${roomIndex}" data-room-field="${field}" ${
      items.length ? "" : "disabled"
    }>${items
      .map(
        (item) =>
          `<option value="${this._escape(item.entity_id)}" ${
            selectedSet.has(item.entity_id) ? "selected" : ""
          }>${this._escape(this._entityLabel(item))}</option>`
      )
      .join("")}</select><small>${
      items.length ? this._escape(help) : "No eligible entities are assigned to this Area in Home Assistant."
    }</small></label>`;
  }

  _bindEvents() {
    this.shadowRoot.querySelectorAll("[data-view]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = button.dataset.view;
        if (next === this._view) return;
        if (this._dirty && this._view === "setup" && !window.confirm("Discard unsaved setup changes?")) return;
        this._view = next;
        this._dirty = false;
        this._draft = this._copy(this._configuration.zones || []);
        this._notice = "";
        this._error = "";
        this._render();
      });
    });
    this.shadowRoot.querySelector('[data-action="reload-all"]')?.addEventListener("click", () => {
      this._started = false;
      this._initialLoad();
    });
    this.shadowRoot.querySelector('[data-action="select-entry"]')?.addEventListener("change", async (event) => {
      if (this._dirty && !window.confirm("Discard unsaved setup changes?")) {
        event.target.value = this._entryId;
        return;
      }
      this._entryId = event.target.value;
      await this._loadConfiguration();
    });
    this.shadowRoot.querySelectorAll("[data-zone-field]").forEach((control) => {
      control.addEventListener("change", () => {
        const zone = this._draft[Number(control.dataset.zone)];
        const field = control.dataset.zoneField;
        zone[field] = field === "reenable_delay" ? Number(control.value) : control.value || null;
        this._markChanged();
      });
    });
    this.shadowRoot.querySelectorAll("[data-room-field]").forEach((control) => {
      control.addEventListener("change", () => {
        const room = this._draft[Number(control.dataset.zone)].rooms[Number(control.dataset.room)];
        const field = control.dataset.roomField;
        room[field] =
          field === "active"
            ? control.checked
            : Array.from(control.selectedOptions).map((option) => option.value);
        this._markChanged();
      });
    });
    this.shadowRoot.querySelectorAll('[data-action="add-room"]').forEach((control) => {
      control.addEventListener("change", () => this._addRoom(control));
    });
    this.shadowRoot.querySelectorAll('[data-action="remove-room"]').forEach((button) => {
      button.addEventListener("click", () => this._removeRoom(button));
    });
    this.shadowRoot.querySelectorAll('[data-action="remove-zone"]').forEach((button) => {
      button.addEventListener("click", () => this._removeZone(button));
    });
    this.shadowRoot.querySelectorAll('[data-action="add-zone"]').forEach((button) => {
      button.addEventListener("click", () => this._addZone());
    });
    this.shadowRoot.querySelector('[data-action="reset"]')?.addEventListener("click", () => {
      this._draft = this._copy(this._configuration.zones || []);
      this._dirty = false;
      this._error = "";
      this._render();
    });
    this.shadowRoot.querySelector('[data-action="save"]')?.addEventListener("click", () => this._save());
  }

  _markChanged() {
    this._dirty = true;
    this._notice = "";
    this._error = "";
    this._render();
  }

  _addZone() {
    const id = globalThis.crypto?.randomUUID
      ? globalThis.crypto.randomUUID()
      : `zone-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    this._draft.push({
      zone_id: id,
      name: `Zone ${this._draft.length + 1}`,
      switch: null,
      heat_source: "ashp",
      reenable_delay: 300,
      ashp_capability: "heat_only",
      rooms: [],
    });
    this._markChanged();
  }

  _removeZone(button) {
    const index = Number(button.dataset.zone);
    const zone = this._draft[index];
    if (!window.confirm(`Remove ${zone.name} and its room assignments?`)) return;
    this._draft.splice(index, 1);
    this._markChanged();
  }

  _addRoom(control) {
    const areaId = control.value;
    if (!areaId) return;
    const area = this._configuration.catalog.areas.find((item) => item.area_id === areaId);
    this._draft[Number(control.dataset.zone)].rooms.push({
      room_id: areaId,
      name: area?.name || areaId,
      trvs: [],
      sensors: [],
      active: true,
      cooling_capable: false,
    });
    this._markChanged();
  }

  _removeRoom(button) {
    const zone = this._draft[Number(button.dataset.zone)];
    const roomIndex = Number(button.dataset.room);
    const room = zone.rooms[roomIndex];
    if (!window.confirm(`Remove ${room.name || this._areaName(room.room_id)} from this zone?`)) return;
    zone.rooms.splice(roomIndex, 1);
    this._markChanged();
  }

  async _save() {
    if (this._saving || !this._dirty) return;
    const invalidName = this._draft.find((zone) => !String(zone.name || "").trim());
    if (invalidName) {
      this._error = "Every zone needs a name.";
      this._render();
      return;
    }
    const invalidDelay = this._draft.find(
      (zone) => !Number.isInteger(Number(zone.reenable_delay)) || Number(zone.reenable_delay) < 0 || Number(zone.reenable_delay) > 3600
    );
    if (invalidDelay) {
      this._error = "Every re-enable delay must be a whole number from 0 to 3600 seconds.";
      this._render();
      return;
    }
    this._saving = true;
    this._error = "";
    this._render();
    try {
      const response = await this._hass.callWS({
        type: "zeal/save_hierarchy",
        entry_id: this._entryId,
        expected_revision: this._configuration.revision,
        zones: this._draft,
      });
      this._configuration.zones = this._copy(response.zones);
      this._configuration.revision = response.revision;
      this._draft = this._copy(response.zones);
      this._dirty = false;
      this._notice = "Setup saved. ZEAL is reloading the updated configuration.";
      await this._reloadAfterSave(response.revision);
    } catch (error) {
      this._saving = false;
      const conflict = error?.code === "conflict" || error?.body?.code === "conflict";
      this._error = conflict
        ? "ZEAL changed in another browser or process. Reload the latest setup before trying again."
        : this._message(error, "Setup could not be saved.");
      this._render();
    }
  }

  async _reloadAfterSave(expectedRevision) {
    for (let attempt = 0; attempt < 12; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 350));
      try {
        const configuration = await this._hass.callWS({
          type: "zeal/get_configuration",
          entry_id: this._entryId,
        });
        if (configuration.revision === expectedRevision) {
          this._saving = false;
          this._acceptConfiguration(configuration);
          return;
        }
      } catch (_error) {
        // A short not-loaded window is expected while Home Assistant reloads.
      }
    }
    this._saving = false;
    this._notice = "Setup saved. Reload this page if the refreshed values do not appear shortly.";
    this._render();
  }

  _styles() {
    return `<style>
      :host { display:block; min-height:100%; color:var(--primary-text-color); background:var(--primary-background-color); font-family:var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
      * { box-sizing:border-box; }
      button, input, select { font:inherit; }
      main { padding:24px 18px 110px; }
      .shell { max-width:1180px; margin:0 auto; }
      header { display:flex; align-items:center; justify-content:space-between; gap:24px; margin-bottom:18px; }
      .identity { display:flex; align-items:center; gap:14px; }
      .identity img { width:52px; height:52px; object-fit:contain; }
      h1,h2,h3,h4,p { margin-top:0; }
      h1 { font-size:30px; line-height:1; margin:0 0 6px; letter-spacing:.02em; }
      .identity p, .page-heading p, .rooms-heading p, .room-editor-title p { color:var(--secondary-text-color); margin:0; }
      .entry-picker { min-width:230px; }
      nav { display:flex; gap:8px; margin-bottom:22px; border-bottom:1px solid var(--divider-color); }
      .tab { appearance:none; background:transparent; border:0; border-bottom:3px solid transparent; color:var(--secondary-text-color); cursor:pointer; padding:12px 18px; }
      .tab.active { border-bottom-color:var(--primary-color); color:var(--primary-color); font-weight:600; }
      .page-heading { display:flex; justify-content:space-between; align-items:flex-start; gap:18px; margin-bottom:18px; }
      .page-heading h2 { font-size:24px; margin-bottom:5px; }
      button { border-radius:6px; border:0; min-height:40px; padding:0 16px; cursor:pointer; }
      button:disabled { opacity:.5; cursor:not-allowed; }
      .primary, .secondary { background:var(--primary-color); color:var(--text-primary-color, white); }
      .secondary { background:var(--secondary-background-color); color:var(--primary-text-color); border:1px solid var(--divider-color); }
      .text-button, .danger-link { background:transparent; color:var(--primary-color); }
      .danger-link { color:var(--error-color); min-height:34px; padding:0 6px; }
      .safety-warning { display:flex; gap:13px; padding:16px; margin:0 0 20px; border:1px solid var(--warning-color, #f4b400); border-radius:10px; background:color-mix(in srgb, var(--warning-color, #f4b400) 12%, var(--card-background-color)); }
      .safety-warning p { margin:5px 0 0; line-height:1.45; color:var(--secondary-text-color); }
      .warning-icon { flex:0 0 26px; width:26px; height:26px; border-radius:50%; display:grid; place-items:center; font-weight:800; color:#111; background:var(--warning-color, #f4b400); }
      .summary-grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:14px; margin-bottom:18px; }
      .summary-card, .zone-card, .setup-zone, .empty-card, .setup-help { background:var(--card-background-color); border:1px solid var(--divider-color); box-shadow:var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,.08)); border-radius:12px; }
      .summary-card { display:flex; align-items:center; gap:14px; padding:18px; }
      .summary-card ha-icon { color:var(--primary-color); --mdc-icon-size:30px; }
      .summary-card strong { display:block; font-size:26px; line-height:1; }
      .summary-card span { display:block; margin-top:5px; color:var(--secondary-text-color); }
      .zone-grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:16px; }
      .zone-card { padding:18px; }
      .zone-title, .setup-zone-title, .room-editor-title, .rooms-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; }
      .zone-title h3, .setup-zone-title h3, .room-editor-title h4, .rooms-heading h4 { margin-bottom:4px; }
      .zone-title p { color:var(--secondary-text-color); margin:0; }
      .pill, .state { white-space:nowrap; border-radius:999px; padding:5px 9px; font-size:12px; background:var(--secondary-background-color); }
      .state { color:var(--success-color, #2e7d32); }
      .state.inactive { color:var(--secondary-text-color); }
      .zone-facts { margin:16px 0; padding:12px 0; border-top:1px solid var(--divider-color); border-bottom:1px solid var(--divider-color); }
      .zone-facts div { display:grid; grid-template-columns:125px minmax(0,1fr); gap:10px; padding:4px 0; }
      dt { color:var(--secondary-text-color); }
      dd { margin:0; overflow-wrap:anywhere; }
      .room-list { display:grid; gap:8px; }
      .room-summary { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:10px; border-radius:8px; background:var(--secondary-background-color); }
      .room-summary strong, .room-summary span { display:block; }
      .room-summary div > span { margin-top:3px; font-size:12px; color:var(--secondary-text-color); }
      .empty-card { padding:28px; text-align:center; }
      .empty-card p { color:var(--secondary-text-color); }
      .setup-help { padding:16px; margin-bottom:16px; }
      .setup-help p { margin:5px 0 0; color:var(--secondary-text-color); }
      .setup-zones { display:grid; gap:18px; }
      .setup-zone { padding:18px; }
      .setup-zone-title { border-bottom:1px solid var(--divider-color); padding-bottom:10px; margin-bottom:15px; }
      .form-grid, .equipment-grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:14px; }
      label { display:flex; flex-direction:column; gap:6px; font-weight:500; }
      input, select { width:100%; min-height:42px; padding:8px 10px; color:var(--primary-text-color); background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:6px; }
      select[multiple] { min-height:76px; padding:4px; }
      select[multiple] option { padding:7px; border-radius:4px; }
      small { color:var(--secondary-text-color); font-weight:400; line-height:1.35; }
      .rooms-heading { align-items:center; margin:22px 0 12px; }
      .add-room { width:auto; min-width:230px; }
      .room-editors { display:grid; gap:12px; }
      .room-editor { border:1px solid var(--divider-color); border-radius:10px; padding:15px; }
      .control-boundary { margin:0 0 14px; padding:13px; border-left:4px solid var(--primary-color); border-radius:6px; background:var(--secondary-background-color); }
      .control-boundary p { margin:4px 0 0; color:var(--secondary-text-color); }
      .control-boundary ul { display:grid; gap:5px; padding:0; margin:10px 0 0; list-style:none; }
      .control-boundary li { display:flex; justify-content:space-between; gap:12px; }
      .control-boundary code { color:var(--secondary-text-color); overflow-wrap:anywhere; text-align:right; }
      .active-toggle { flex-direction:row; align-items:flex-start; margin:12px 0; }
      .active-toggle input { width:20px; min-height:20px; margin:1px 2px 0 0; }
      .active-toggle span, .active-toggle strong, .active-toggle small { display:block; }
      .canonical-target { display:flex; align-items:flex-start; gap:10px; padding:12px; margin:0 0 14px; border-radius:8px; background:var(--secondary-background-color); }
      .canonical-target ha-icon { color:var(--primary-color); margin-top:1px; }
      .canonical-target strong, .canonical-target span, .canonical-target small { display:block; }
      .canonical-target span { margin:3px 0; overflow-wrap:anywhere; }
      .room-empty { padding:18px; text-align:center; color:var(--secondary-text-color); border:1px dashed var(--divider-color); border-radius:8px; }
      .save-bar { position:sticky; bottom:12px; z-index:2; display:flex; justify-content:space-between; align-items:center; gap:14px; padding:12px 14px; margin-top:18px; background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:10px; box-shadow:0 5px 20px rgba(0,0,0,.18); }
      .save-bar > div { display:flex; gap:8px; }
      .save-state { color:var(--secondary-text-color); }
      .message { border-radius:8px; padding:12px 14px; margin:0 0 16px; }
      .message.error { color:var(--error-color); background:color-mix(in srgb, var(--error-color) 10%, var(--card-background-color)); border:1px solid var(--error-color); }
      .message.success { color:var(--success-color, #2e7d32); background:color-mix(in srgb, var(--success-color, #2e7d32) 10%, var(--card-background-color)); border:1px solid var(--success-color, #2e7d32); }
      .center-state { min-height:55vh; display:grid; place-content:center; justify-items:center; color:var(--secondary-text-color); }
      .spinner { width:34px; height:34px; border:4px solid var(--divider-color); border-top-color:var(--primary-color); border-radius:50%; animation:spin .8s linear infinite; }
      .muted { color:var(--secondary-text-color); }
      @keyframes spin { to { transform:rotate(360deg); } }
      @media (max-width: 760px) {
        main { padding:16px 10px 100px; }
        header, .page-heading { align-items:stretch; flex-direction:column; }
        .identity img { width:46px; height:46px; }
        .entry-picker { min-width:0; }
        nav { display:grid; grid-template-columns:1fr 1fr; }
        .tab { padding:12px 8px; }
        .summary-grid, .zone-grid, .form-grid, .equipment-grid { grid-template-columns:1fr; }
        .summary-grid { grid-template-columns:repeat(3, 1fr); }
        .summary-card { display:block; padding:12px; text-align:center; }
        .summary-card ha-icon { margin-bottom:6px; }
        .summary-card strong { font-size:22px; }
        .summary-card span { font-size:12px; }
        .zone-facts div { grid-template-columns:1fr; gap:2px; }
        .control-boundary li { align-items:flex-start; flex-direction:column; }
        .control-boundary code { text-align:left; }
        .room-summary { align-items:flex-start; }
        .rooms-heading { align-items:stretch; flex-direction:column; }
        .add-room { width:100%; }
        .save-bar { align-items:stretch; flex-direction:column; bottom:8px; }
        .save-bar > div { display:grid; grid-template-columns:1fr 1fr; }
        .safety-warning { padding:13px; }
      }
      @media (max-width: 430px) {
        .summary-grid { grid-template-columns:1fr; }
        .summary-card { display:flex; text-align:left; }
        .setup-zone { padding:14px; }
        .room-editor { padding:12px; }
      }
    </style>`;
  }
}

if (!customElements.get("zeal-panel")) {
  customElements.define("zeal-panel", ZealPanel);
}
