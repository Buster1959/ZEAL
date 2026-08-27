# ZEAL automated tests

Automated tests for the Coordinator's demand/safety logic and the pure ZEAL
scheduler domain. The suite covers combinations that would take substantial
time to click through by hand in a live development environment and runs in
well under a second.

Coverage: 130 collected cases against `pytest-homeassistant-custom-component`:
39 Coordinator cases, 35 pure scheduler cases, 14 scheduler runtime/boundary
cases, 24 configuration/audit/WebSocket cases and 6 Config Flow/HTML panel
contract cases, plus one translation-schema case covering ten languages and
three release-metadata cases. Test code is kept under `tests/`, not shipped
inside `custom_components/zeal`. Verified result: 130/130 passing.

## Running

```bash
python3 -m venv venv
venv/bin/pip install -r requirements_test.txt
venv/bin/python -m pytest tests/ -v
```

No real Home Assistant install needed — `pytest-homeassistant-custom-component`
provides a real (but isolated, in-memory) `hass` test instance, the same
framework Home Assistant Core itself uses to test its own integrations.

## What's covered

- `_room_temperature` — single sensor, averaging multiple sensors,
  ignoring unavailable ones, all-unavailable/no-sensors returning `None`.
- `_evaluate_zone` — the room-by-room demand threshold (`Setpoint −
  Temperature > 0`), any-one-room-demanding triggering the whole zone,
  inactive rooms never contributing, a thermostat in `hvac_mode: off`
  being skipped, and the fallback to highest-TRV-setpoint when a room's
  `ZealRoomThermostat` hasn't registered yet.
- `_zone_all_trvs_off` — the pump-protection override: fires only when
  every TRV is *confirmed* off, never on an unavailable/uncertain
  reading, and ignores inactive rooms' TRVs.
- The self-write loop guard — reproduces the exact incident where a
  `ZealRoomThermostat` ended up in its own room's TRV list, confirming
  propagation skips it rather than recursing.
- Setpoint safety clamping at the physical TRV write boundary.
- Debounced unavailable-device notifications, recovery dismissal and remaining
  room-coverage messages.
- Zigbee-style stale readings, including exclusion from temperature averaging
  and conservative all-TRVs-off pump protection.
- Versioned ZEAL schedule serialization and migration, exact time validation,
  stable room-ID reconciliation and a separate Store boundary.
- Active/next-period calculation across midnight and empty days, schedule copy
  isolation, and temporary override targets/expiry without editing schedules.
- Startup reconciliation, nearest-transition timing, unavailable-room retry,
  unload cleanup and exclusive use of ZEAL's clamped canonical room boundary.
- Admin-only WebSocket authorization, registry-backed hierarchy validation,
  optimistic revision conflicts, reload persistence, Quick Change, bounded
  audit retention and JSON-safe configuration/audit downloads.
- Separate entity catalogs prove ZEAL-owned canonical scheduling thermostats
  cannot appear in the physical room thermostat or temperature-sensor pickers.
- Admin-only ZEAL panel registration, integration configuration routing, static
  asset registration, safe-save API use, responsive breakpoints and the
  competing-scheduler warning contract.
- Seven-day visual editor contracts for exact entry, drag controls,
  cross-midnight carry, source-day application and room copying, plus a live
  WebSocket save/copy cycle proving destination identity and equipment remain
  unchanged.
- Quick Change selection/duration/hold/cancel contracts, proof that runtime
  holds do not mutate the saved schedule, timestamped JSON download wiring and
  persisted audit recovery through a fresh runtime instance.
- Calendar and exact-date-range Away activation, active-room scoping, start/end
  timers, restart reconciliation, hold pause/resume, manual-change reassertion,
  Quick Change rejection and unchanged Zone Manual Override actuator authority.
- Complete, non-empty config-flow translation schemas for all ten shipped
  language files.
- HACS/Home Assistant manifest identity, Hassfest key ordering and both
  repository validation workflow contracts.

## What's NOT covered (yet)

Browser DOM interactions and visual rendering, the `switch`/`sensor`/`climate`
entity platforms themselves (as opposed to the Coordinator logic they call
into), and cooling. Contributions extending coverage welcome — this
is meant to grow alongside the project, not stay fixed at this snapshot.

## Adding a test for a new bug

If you find a bug the way several were found in this project's own
Decisions Log (the infinite-recursion incident, the all-TRVs-off gap,
etc.) — write a test that reproduces it *before* fixing the code, confirm
it fails, then fix and confirm it passes. Keeps the exact scenario that
bit someone once from silently regressing later.
