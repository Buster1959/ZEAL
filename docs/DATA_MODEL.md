# ZEAL V1 Data Model

ZEAL persists three deliberately separate documents for each Home Assistant
config entry. Separating them prevents runtime timing state, user configuration
and schedule history from accidentally replacing one another.

## Zone and room hierarchy

Zone configuration is stored in config-entry options under `zones`.

```json
{
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

Configuration and audit downloads necessarily include room/zone names and
entity IDs. Review exports before sharing if those names reveal personal
information.
