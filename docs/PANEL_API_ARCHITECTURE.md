# ZEAL Panel API Architecture

Status: Block 4 backend complete; HTML consumers begin in Block 5.

## Security boundary

Every `zeal/*` WebSocket command is protected by Home Assistant's admin-user
requirement. A read-only authenticated user is rejected before configuration,
entity catalog, Quick Change or download data is returned. Each command also
requires an explicit loaded config-entry ID; no command silently selects the
first ZEAL instance.

The hierarchy writer treats browser data as untrusted. It validates:

- unique zone IDs, Area/room IDs, zone switches and room equipment;
- Areas and entities against Home Assistant's current registries;
- correct `switch`, `climate` and temperature-`sensor` domains/classes;
- that selected room equipment belongs to the selected Area;
- that disabled or ZEAL-owned entities cannot be selected as physical devices;
- heat-source values, boolean room state and the 0–3600 second re-enable range;
- schedules, times and temperatures through the versioned model, including the
  5–30°C ZEAL safety range.

## Conflict protection

Read responses contain a deterministic `revision` derived from both saved
hierarchy and schedule documents. Every hierarchy or schedule write must include
the revision it was edited from. If either document changed in another browser
tab or after a reload, the write fails with `conflict`; the newer data is never
overwritten.

## Commands

- `zeal/list_entries`: loaded ZEAL instances.
- `zeal/get_configuration`: hierarchy, schedule, Quick Change state, revision
  and eligible Area/entity catalog.
- `zeal/save_hierarchy`: validated full hierarchy update and safe config-entry
  reload.
- `zeal/update_room_days`: validated seven-day update for one stable room ID.
- `zeal/copy_room_schedule`: save source editor state and copy only its daily
  periods to selected rooms.
- `zeal/get_quick_change`, `zeal/set_temporary_override` and
  `zeal/clear_temporary_override`: transient targets that never edit schedules.
- `zeal/export_configuration`: JSON-ready hierarchy/schedule download document.
- `zeal/get_audit_log`: JSON-ready bounded application history.

## Persistence and runtime ordering

Schedule writes are validated, persisted, then applied to the running scheduler.
Hierarchy writes are validated, reconcile schedule records to the new stable
room IDs, persist the reconciled schedule, update config-entry options and let
the standard ZEAL update listener reload the integration. Automated coverage
proves the hierarchy and reconciled schedule survive this reload.

## Audit privacy and retention

The audit Store is separate from configuration and Coordinator state. It keeps
the newest 500 canonical room-target outcomes. Records contain timestamp, stable
room ID/name, canonical ZEAL thermostat ID, previous/requested temperature,
cause and outcome. They do not contain credentials, tokens, location coordinates
or physical-TRV service payloads.

The HTML panel will turn the returned export objects into browser downloads;
the backend does not write files into Home Assistant's configuration directory.
