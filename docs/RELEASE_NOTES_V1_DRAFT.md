# ZEAL V1 Release Notes — Draft

These notes describe the intended first stable ZEAL release. They remain a
draft until Block 10 live acceptance passes and the manifest version is changed
to `1.0.0`.

## Highlights

- Native Home Assistant zone/room/TRV/sensor setup through an admin-only panel.
- One canonical ZEAL room thermostat with synchronized physical TRVs.
- Safe zone-demand control, re-enable delays, Manual override and device-health
  notifications.
- Seven-day visual schedules with exact editing, day application and room copy.
- Temporary Quick Change for rooms, zones, selections or the whole house.
- Calendar or exact-date Away mode with an immediate **End Away now** action.
- Downloadable configuration and bounded persistent application audit trail.
- Optional sidebar navigation and clear per-instance management/deletion.
- HACS metadata, HACS/Hassfest workflows and setup-flow translations for ten
  European languages including English.

## Important safety note

Do not let ZEAL and another thermostat setpoint scheduler control the same
thermostat entities. Test first with dummy/spare equipment and complete the live
acceptance plan before unattended use.

## Known V1 limits

- Heating only; the reserved cooling fields have no runtime effect.
- Scheduler and ZEAL panel targets use Celsius in V1.
- The ZEAL HTML panel is English even when the Home Assistant setup flow is
  translated.
- The final `1.0.0` manifest and GitHub release follow Block 10 validation.
- ZEAL remains under PolyForm Shield and is distributed through HACS as a
  custom repository. The licence is intentionally retained, so this release is
  not intended for the default HACS store.
