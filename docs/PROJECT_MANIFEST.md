# ZEAL Project Manifest

## Identity

- Repository: `Buster1959/ZEAL`
- Home Assistant domain: `zeal`
- Integration folder: `custom_components/zeal`
- Integration name: ZEAL HVAC System
- Integration type: helper
- Distribution target: HACS custom integration
- Current development branch: `feature/v1-scheduler-html-ui`
- Current manifest version: `0.13.0` (pre-V1)

## Independence boundary

ZEAL includes its own scheduler and works without Visual Climate Scheduler.
Visual Climate Scheduler works without ZEAL. Users should not let ZEAL or any
other thermostat setpoint scheduler control the same thermostat entities.

## V1 status

Blocks 0–8 are implemented. Block 9 adds HACS metadata, validation workflows,
setup-flow translations and aligned repository/Wiki documentation. Actual ZEAL
screenshots remain a privacy-review gate and must be captured from a generic
test installation. Block 10 performs live acceptance, version finalisation,
release notes and the reviewable merge to `main`. PolyForm Shield remains the
project licence during full testing; the licence decision required for a clean
HACS validation result is deliberately deferred until testing is complete.
The automated and live gates are tracked in `docs/V1_ACCEPTANCE_RECORD.md`.

## Validation commands

```bash
python -m pytest tests/ -q
python -m compileall -q custom_components tests
```

GitHub runs both HACS validation and Home Assistant Hassfest on pushes and pull
requests. Hassfest passes. HACS currently reports only the unrecognised
PolyForm Shield licence, which is a recorded deferred release decision. Passing
both workflows will still be required before a default-store request and does
not replace live thermostat/actuator testing.
