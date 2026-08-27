# ZEAL Instructions for Use — V1 Draft

ZEAL combines room thermostats, heating-demand control and a weekly visual
scheduler in one Home Assistant integration. V1 is still being prepared; use
dummy or spare equipment first and complete the live test plan before relying
on it for unattended heating.

## Before installing

- Create a Home Assistant Area for every room you want ZEAL to control.
- Assign each physical climate thermostat/TRV and temperature sensor to its
  room Area.
- Have one Home Assistant `switch` entity for each zone's pump, relay or other
  heating actuator.
- ZEAL V1's scheduler and setup panel use Celsius targets.
- Disable any other scheduler, automation or blueprint that changes the same
  thermostat setpoints. Competing writers can overwrite each other.

## Install

Until ZEAL is accepted into the default HACS store, add
`https://github.com/Buster1959/ZEAL` as a HACS custom repository in the
**Integration** category, install ZEAL and restart Home Assistant.

For a manual installation, copy `custom_components/zeal` into
`config/custom_components/zeal` and restart Home Assistant.

Then open **Settings → Devices & Services → Add Integration**, search for
**ZEAL HVAC System**, give the instance a name and finish. ZEAL appears in the
sidebar for Home Assistant administrators.

## Set up zones and rooms

Open **ZEAL → Setup**. Add a Zone/Floor, select its single heating actuator and
heat source, then review the suggested re-enable delay. Add one or more Home
Assistant Areas as rooms and choose the non-ZEAL physical thermostats/TRVs and
temperature sensors in each Area. Mark unused rooms inactive and save.

The physical equipment picker intentionally excludes ZEAL's own room
thermostats. After saving, use **Overview** to confirm the hierarchy, actuator,
heat source, delay and equipment counts. Overview also shows the local time and
setpoint of each room's latest successful ZEAL target change.

Setup also contains **Show ZEAL in the Home Assistant sidebar**. Clear it and
select **Save setup** if you do not want a permanent sidebar link. ZEAL keeps
running. To restore the link, open **Settings → Devices & Services → ZEAL HVAC
System → Configure**, enable the recovery checkbox and submit. The full panel
also remains available directly at `/zeal`.

## Build and copy schedules

Open **Schedule**, choose a Zone/Floor and room, and add up to four changes to
each day. Drag graph points for quick changes or enter the exact time and target
below the graph. Select one Source day and any Apply-here days to copy a daily
pattern before saving. Use **Select all days** or **Clear all days** for every
destination except the Source.

The last target carries across midnight and empty days. To reuse a full week,
expand the room-copy section and select destination rooms. Their names, Areas,
equipment and canonical thermostats do not change.

## Make a temporary Quick Change

Open **Quick Change**, select one room, a Zone/Floor, several rooms or the whole
house, then choose −1°C, +1°C or an exact target. Select two hours, four hours
or until the next schedule transition. Cancel a room's hold to return it to the
current weekly target. The saved schedule is never edited.

## Use Away mode

Open **Setup → Away mode** and select Off, a dedicated Home Assistant Calendar,
or one exact start/end period. Manual date/time choices use five-minute
intervals. Choose the global Away target and save. Away applies to every active
room in all zones; no separate zone selection is needed. If you return early,
select **End Away now**; normal control resumes immediately.

While Away is active, new Quick Changes are blocked. Existing holds pause and
resume afterward only if they have not expired.

## Download configuration and audit trail

Open **Setup → Downloads** and select **Download configuration** or **Download
audit trail**. The configuration export contains the saved hierarchy,
equipment, schedules and Away settings. The audit export contains up to 500
recent target attempts and outcomes.

Exports contain room/zone names and entity IDs, but no credentials or tokens.
Review them before sharing if your naming reveals personal information.

## Multiple ZEAL instances

Separate named ZEAL instances can control separate heating systems on one Home
Assistant machine. Their thermostats, sensors and actuators must not overlap.
Use the instance selector in the ZEAL header to change which one you are
viewing. To delete only the selected one, open **Setup → ZEAL instance
management**, select **Delete this ZEAL instance** and confirm the permanent
removal. Its setup, schedules and audit trail are deleted; other instances are
not changed. Select **Open integration settings** to use Home Assistant's native
page when you want to disable an individual instance instead.
The shared sidebar link remains visible while any loaded ZEAL instance has its
sidebar option enabled; it is hidden only when every loaded instance disables
the option.

## Mobile use

Use the Home Assistant Companion app or a mobile browser and open ZEAL from the
sidebar. The pages use a single-column layout on narrow screens. For accurate
editing:

- use exact time and target fields when dragging a graph point is awkward;
- scroll within the page rather than using browser zoom;
- save before leaving Schedule or Setup;
- use Quick Change for routine temporary changes rather than editing a week;
- verify the confirmation or updated status after every save.

## Troubleshooting

See [Troubleshooting](TROUBLESHOOTING.md) for equipment discovery, cache,
logging, scheduling and Away checks. For a full dummy-system walkthrough, use
the repository [test plan](../TEST_PLAN.md).
