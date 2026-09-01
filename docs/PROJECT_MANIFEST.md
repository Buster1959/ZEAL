# ZEAL Project Manifest

## Identity

- Repository: `Buster1959/ZEAL`
- Home Assistant domain: `zeal`
- Integration folder: `custom_components/zeal`
- Integration name: ZEAL HVAC System
- Integration type: hub
- Distribution target: HACS custom integration
- Current release-candidate branch: `main`
- Current manifest version: `0.14.7` (pre-V1)

## Independence boundary

ZEAL includes its own scheduler and works without Visual Climate Scheduler.
Visual Climate Scheduler works without ZEAL. Users should not let ZEAL or any
other thermostat setpoint scheduler control the same thermostat entities.

## ZEAL Flow naming boundary

`Buster1959/ZEAL-flow` is currently the public mechanical retrofit project. The
planned private heating-and-cooling V2 project has also been described as
**ZEAL Flow**. That collision is unresolved; documentation and project skills
must not silently assign the name to only one of them. Work referring to ZEAL
Flow must identify the intended repository until a distinct product name is
chosen.

## V1 status

Blocks 0–9 are implemented and the V1 candidate has been fast-forwarded to
`main`. Block 10 live regression testing is in progress; feedback fixes must be
retested before version finalisation, tagging and release. Privacy-reviewed
desktop screenshots from the generic test installation are now documented;
the mobile captures remain a release gate. PolyForm Shield remains the
project licence for V1. ZEAL is therefore distributed through HACS as a custom
repository rather than submitted to the default HACS store.
The automated and live gates are tracked in `docs/V1_ACCEPTANCE_RECORD.md`.

## Validation commands

```bash
python -m pytest tests/ -q
python -m compileall -q custom_components tests
```

GitHub runs both HACS validation and Home Assistant Hassfest on pushes and pull
requests. Hassfest passes. HACS currently reports only the unrecognised
PolyForm Shield licence. That expected policy result is retained for visibility
but is not a custom-repository or V1 release blocker. All technical metadata
checks and Hassfest must still pass; none replace live thermostat/actuator
testing.
