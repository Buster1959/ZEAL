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
release notes and the reviewable merge to `main`.

## Validation commands

```bash
python -m pytest tests/ -q
python -m compileall -q custom_components tests
```

GitHub runs both HACS validation and Home Assistant Hassfest on pushes and pull
requests. Passing those workflows confirms repository structure; it does not
replace live thermostat/actuator testing.
