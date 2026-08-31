# ZEAL live test automations

## Schedule Adaptation holiday test — 1–6 September 2026

[`schedule-adaptation-holiday-test.yaml`](schedule-adaptation-holiday-test.yaml)
is generated specifically from the ZEAL configuration exported on 31 August
2026. It targets the canonical ZEAL room thermostats and the schedule values in
that export. Do not reuse it after changing those rooms, entity IDs or periods.

Before enabling it:

1. Update ZEAL to `0.14.3`, restart Home Assistant and hard-refresh the browser.
2. Enable **Setup → ZEAL Learning → Enable Schedule Adaptation**.
3. Confirm Home Assistant's time zone is Europe/London and all four canonical
   thermostat entities in the automation exist.
4. Confirm the physical heat source is intentionally disabled. ZEAL may still
   show demand and operate the configured dummy actuator switches during the
   five-minute test changes.
5. Do not edit the tested schedule or ZEAL Setup during the six days. Either
   action changes the configuration revision and deliberately separates the
   evidence.

The automation makes each test request for five minutes and then restores the
scheduled target. A restoration that matches the active schedule is ignored by
Learning and does not count as opposite evidence.

Expected proposals:

| Evidence dates | Room | Expected proposal |
|---|---|---|
| 1–3 September | Bathroom | Move the 14:00, 18°C period earlier to 13:40 |
| 1–3 September | Lounge | Change the 16:00 target from 20°C to 21.5°C |
| 1–3 September | Dining Room | Change the 16:00 target from 18°C to 16.5°C |
| 4–6 September | Master Bedroom | Move the 14:00, 18°C period later to 14:20 |

On return, use different proposals to exercise **Accept**, **Edit and accept**
and **Dismiss**. Accept and edited-accept change only the weekday on which the
third event raised that proposal. Test **Revert schedule change** on accepted
history before making any unrelated schedule edit. Dismissed proposals require
three materially new qualifying dates before they can be offered again.

Disable or delete the automation after the completion notification on 6
September. The automation expires by date and will take no action after that
day, but removing it avoids future confusion.
