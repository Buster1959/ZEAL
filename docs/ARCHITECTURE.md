# ZEAL Architecture

ZEAL is one self-contained Home Assistant custom integration. It owns its
configuration UI, room thermostat entities, heating-demand coordinator,
scheduler, temporary holds, Away mode, persistence and audit trail.

It does not import or call Visual Climate Scheduler. The two integrations can
be installed independently. They should not both schedule the same physical
thermostat because competing setpoint writers can repeatedly overwrite each
other.

## Runtime layers

1. **Config entry and panel** — `__init__.py`, `config_flow.py`, `panel.py` and
   `frontend/zeal-panel.js` register the integration and its admin-only panel.
2. **Validated API** — `scheduler/websocket_api.py` and
   `scheduler/configuration.py` authorize, validate and conflict-protect every
   panel read or write.
3. **Durable models** — zone/room configuration is held in config-entry
   options; schedules, Away settings and audit entries use separate versioned
Home Assistant stores.
4. **Scheduler runtime** — `scheduler/runtime.py` resolves Away, Quick Change,
   manual thermostat changes and weekly schedules, then writes only to the
   canonical ZEAL room thermostat.
5. **Heating control** — `coordinator.py` propagates that room target to the
   configured physical TRVs, evaluates room demand and safely controls the
   zone actuator.

Each config entry owns independently keyed Coordinator, schedule and audit
stores. Multiple entries can therefore run separate heating systems. Removing
one entry deletes only those three stores; the panel remains registered while
another ZEAL entry is loaded.

## Entity boundary

Each configured room has one stable room ID and one ZEAL-owned climate entity.
Schedules target that canonical room thermostat, never an individual physical
TRV. Setup keeps two separate catalogs:

- ZEAL room thermostats are shown as scheduling targets.
- Non-ZEAL climate entities in the room's Home Assistant Area are shown as
  physical thermostat/TRV choices.

The separation uses Home Assistant entity-registry ownership, so renaming an
entity cannot make a ZEAL thermostat selectable as its own physical TRV.

## Safety and precedence

Room target precedence is:

1. active Away mode;
2. active Quick Change hold;
3. a manual ZEAL room-thermostat change until the next transition;
4. the weekly schedule.

The per-zone Manual override is separate and remains the highest authority over
the physical actuator. Every target passes through ZEAL's 5–30°C clamp before
it can reach a physical thermostat. Unavailable or stale readings are excluded
from decisions, and an all-valves-closed result forces the zone actuator off.

## Further technical detail

- [ZEAL Learning roadmap](LEARNING_ROADMAP.md)
- [Panel API architecture](PANEL_API_ARCHITECTURE.md)
- [Scheduler architecture](SCHEDULER_ARCHITECTURE.md)
- [Data model](DATA_MODEL.md)
- [Decision summary](DECISIONS.md)
