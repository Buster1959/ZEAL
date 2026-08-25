# ZEAL automated tests

Automated tests for the Coordinator's demand/safety logic and the pure ZEAL
scheduler domain. The suite covers combinations that would take substantial
time to click through by hand in a live development environment and runs in
well under a second.

Coverage: 73 collected cases against `pytest-homeassistant-custom-component`:
38 Coordinator cases, 25 pure scheduler cases and 10 scheduler runtime/boundary
cases. Test code is kept under `tests/`, not shipped inside
`custom_components/zeal`. Verified result: 73/73 passing.

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

## What's NOT covered (yet)

Config Flow / Options Flow, the `switch`/`sensor`/`climate` entity
platforms themselves (as opposed to the Coordinator logic they call
into), the HTML interface, runtime temporary-override wiring, away mode and
cooling. Contributions extending
coverage welcome — this is meant to grow alongside the project, not stay
fixed at this snapshot.

## Adding a test for a new bug

If you find a bug the way several were found in this project's own
Decisions Log (the infinite-recursion incident, the all-TRVs-off gap,
etc.) — write a test that reproduces it *before* fixing the code, confirm
it fails, then fix and confirm it passes. Keeps the exact scenario that
bit someone once from silently regressing later.
