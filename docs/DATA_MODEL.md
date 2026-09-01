# ZEAL V1 Data Model

ZEAL persists four deliberately separate documents for each Home Assistant
config entry. Separating them prevents runtime timing state, user configuration
and schedule history from accidentally replacing one another.

## Zone and room hierarchy

Zone configuration and the panel-navigation preference are stored in
config-entry options.

```json
{
  "show_in_sidebar": true,
  "zones": [
    {
      "zone_id": "example-zone",
      "name": "Example Floor",
      "switch": "switch.example_heating",
      "heat_source": "ashp",
      "reenable_delay": 300,
      "ashp_capability": "heat_only",
      "rooms": [
        {
          "room_id": "example-area-id",
          "name": "Example Room",
          "trvs": ["climate.example_trv"],
          "sensors": ["sensor.example_temperature"],
          "active": true,
          "cooling_capable": false
        }
      ]
    }
  ]
}
```

`show_in_sidebar` defaults to `true` for entries created before the preference
was introduced. It controls only whether the shared ZEAL link appears in Home
Assistant navigation; it does not enable or disable the integration. With
multiple loaded instances, the link is visible if any instance requests it.

`room_id` is the stable Home Assistant Area ID. One Area can belong to only one
ZEAL zone. `ashp_capability` and `cooling_capable` are reserved safe-default V2
fields; no V1 cooling behavior uses them.

## Schedule document

The version-1 scheduler store contains:

- `version` — schema version, currently `1`;
- `temperature_unit` — `°C`, `°F` or `null` until established;
- `rooms` — a map keyed by stable ZEAL room ID;
- `settings` — integration-wide scheduler settings, including Away mode.

Every room contains exactly Monday through Sunday. Each day is an ordered list
of periods with a stable ID, display names, exact 24-hour `HH:MM` time and a
finite 5–30°C target. A room can have at most four periods per day through the
V1 editor.

A period remains effective until a later period takes over, including across
midnight and across empty days. Copying a week duplicates only the schedule;
the destination room's ID, zone, Area and physical equipment are preserved.

## Runtime state

The Coordinator store contains transient safety state such as each zone's last
actuator-off time. Temporary Quick Change holds are runtime state: they do not
edit the saved weekly schedule. Away configuration is durable and is
reconciled against calendar/date state after restart.

## Audit document

The audit store has schema version `1` and retains the newest 500 canonical
room-target outcomes. Each record contains timestamp, stable room identity,
canonical entity ID, previous and requested temperatures, cause and outcome.
It contains no credentials or Home Assistant tokens.

The configuration snapshot exposes the newest successful audit record for each
room as `last_changes`; this is a derived Overview view, not a fourth persisted
document.

### Schedule Adaptation learning audit (`0.14.7`)

Learning uses a separate versioned Store rather than overloading the V1
application audit. The initial event model records a stable event ID, room,
timestamp/local date, source (Home Assistant/canonical thermostat, physical TRV
or Quick Change), requested target, immutable schedule-period baseline and
revision, adaptation type, pattern key and outcome. Source attribution is based
on ZEAL's control boundary and write-echo guards, not inferred from display text.
Room temperature, demand/actuator context, effective target and override expiry
remain planned enrichments; the detector does not claim to use fields it has not
captured.

Repeated-change proposals are stored separately from raw events. A proposal
records its evidence event IDs/count, pattern, immutable current period,
proposed schedule edit and state (`new`, `accepted`, `dismissed`, `snoozed`,
`conflicted` or `reverted`). Accepting or editing a proposal creates a normal
schedule revision and records the approving user and resulting revision; the
learner never mutates the schedule document directly.

The Store retains events for at most 42 days and also caps them at 5,000; it
retains at most 500 proposals. Learning data is
not included in the existing configuration/audit downloads. Any future Learning
export must warn that this history may reveal occupancy routines even though it
contains no Home Assistant credentials.

### Planned room thermal-response documents

Thermal learning should use a separate versioned observation store and derived
per-room model store. Observations distinguish measured outdoor temperature from
forecast temperature and retain source entity, timestamps, room temperatures,
effective/scheduled target, heat-demand/actuator state, optional heat-input and
disturbance signals, validity/exclusion reason and model version.

Each derived room model records its effective thermal mass/heat-loss parameters,
response delay, training range, evidence count, last trained time, model version
and confidence. Raw observations remain the reproducible evidence; derived
parameters can be rebuilt after a model migration. A model never crosses room
IDs, and missing/stale weather data does not modify the saved schedule.

Configuration and audit downloads necessarily include room/zone names and
entity IDs. Review exports before sharing if those names reveal personal
information.
