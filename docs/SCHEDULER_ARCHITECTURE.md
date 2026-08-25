# ZEAL Scheduler Architecture

Status: Block 2 model complete; runtime integration begins in Block 3.

## Independence boundary

ZEAL owns every scheduler module under `custom_components/zeal/scheduler`.
It does not import Visual Climate Scheduler and does not use that integration's
domain, services or storage. The two integrations remain independently
installable.

## Durable model

Each schedule belongs to one stable ZEAL `room_id` and contains:

- the room's current display name;
- exactly seven named weekday lists;
- zero or more ordered time/setpoint periods per day;
- configuration-level JSON-safe settings and the Home Assistant temperature
  unit.

Physical TRV entity IDs, zone switches and ZEAL climate entity IDs are not
persisted in schedule records. That prevents a schedule from bypassing ZEAL's
canonical room thermostat and safety boundary.

The schema is versioned independently from ZEAL's Coordinator runtime Store.
Its Store key is `zeal.scheduler.<config-entry-id>` and its current schema and
Store versions are both 1. Pre-versioned prototype documents migrate to V1;
unknown future versions fail closed.

## Pure modules

- `models.py`: validation, JSON conversion, schema migration and detached
  period copies.
- `engine.py`: active-period and next-transition selection, including
  cross-midnight carry and empty days.
- `editor.py`: validated day replacement and one-time schedule copying while
  retaining each destination room's identity.
- `rooms.py`: reconciliation with the current ZEAL room registry. Renaming a
  room preserves its schedule; a new stable ID gets empty days; a removed ID
  is removed from the schedule document.
- `overrides.py`: temporary absolute/delta targets lasting two hours, four
  hours or until the next scheduled change. Calculations never modify the
  saved weekly schedule.
- `storage.py`: the only Home Assistant-facing module in this package; adapts
  the pure document to a separate versioned `Store`.

## Block 3 runtime rule

The future runtime adapter must resolve each scheduled `room_id` through ZEAL's
configured rooms and apply the effective target through the existing canonical
ZEAL room thermostat/setpoint propagation path. It must never schedule or call
a physical TRV independently.
