# ZEAL Project Manifest

## Identity

- Repository: `Buster1959/ZEAL`
- Home Assistant domain: `zeal`
- Integration folder: `custom_components/zeal`
- Integration name: ZEAL HVAC System
- Integration type: hub
- Distribution target: HACS custom integration
- Current release-candidate branch: `main`
- Current manifest version: `0.13.3` (pre-V1)

## Independence boundary

ZEAL includes its own scheduler and works without Visual Climate Scheduler.
Visual Climate Scheduler works without ZEAL. Users should not let ZEAL or any
other thermostat setpoint scheduler control the same thermostat entities.

## V1 status

Blocks 0–9 are implemented and the V1 candidate has been fast-forwarded to
`main`. Block 10 live regression testing is in progress; feedback fixes must be
retested before version finalisation, tagging and release. Actual ZEAL
screenshots remain a privacy-review gate and must be captured from a generic
test installation. PolyForm Shield remains the
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
