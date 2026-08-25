# ZEAL Scheduler Architecture

Status: Block 2 model and Block 3 runtime integration complete.

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

## Runtime adapter

On config-entry startup, ZEAL loads the independent schedule Store and
reconciles it against the current configured room IDs. New schedulable rooms get
empty schedules, renamed rooms keep their periods, and deleted room IDs are
removed before the reconciled document is saved.

`scheduler/runtime.py` immediately restores the period that should currently be
active, then creates one Home Assistant timer for the nearest upcoming room
transition. At a transition it applies changed periods and arranges the next
timer. Timers and Coordinator listeners are cancelled on unload.

The runtime passes only `room_id`, temperature and cause to
`ZealCoordinator.async_set_room_target`. The Coordinator resolves the canonical
ZEAL room thermostat, clamps the requested temperature, updates that entity and
then uses its existing guarded propagation path for the room's physical TRVs.
The runtime never reads, stores, selects or calls a physical TRV entity ID.

If a configured room thermostat is not currently registered, the application
is skipped and is not marked successful. A later Coordinator update retries the
current period; successfully applied periods are not repeated.
