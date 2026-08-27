# ZEAL Troubleshooting

## A thermostat or sensor is missing from Setup

Confirm the entity is enabled and assigned to the correct Home Assistant Area.
ZEAL-owned room thermostats are intentionally excluded from physical equipment
pickers. Reload ZEAL after changing registry assignments.

## A saved change is rejected as stale

Another browser or process saved newer data. Reload the ZEAL page, review the
current configuration and repeat the edit. The rejection prevents an old page
from overwriting newer settings.

## A schedule did not change the target

Check the control sources shown in ZEAL. Active Away mode takes priority over
Quick Change and the weekly schedule. A Quick Change takes priority over the
week. A manual room-thermostat change is respected until the next schedule
transition during normal control. Also confirm the room is active and has a
canonical ZEAL thermostat.

## A Quick Change is unavailable

Quick Change is deliberately blocked while Away is active. End Away or wait for
its calendar/date source to end.

## Away did not follow a calendar

Use a dedicated `calendar` entity and confirm its current Home Assistant state
is `on` during the event. Reload after changing the selected entity. If you
returned early, **End Away now** switches Away to Off and stops following the
event until configured again.

## The panel shows old text or layout after an update

Restart Home Assistant, then hard-refresh the browser or fully close and reopen
the Companion app. The panel asset is versioned, but an already open WebView can
still retain an earlier document.

## The actuator does not switch

Check the zone's Manual override entity first. When it is on, ZEAL deliberately
leaves the actuator untouched. Also check the re-enable delay, room active
state, usable sensor readings and whether every physical TRV is confirmed
closed.

## ZEAL reports an entity health warning

Read the exact reason in the notification. A state of `unavailable` or
`unknown` is reported by Home Assistant. “Has not reported a state” means the
entity's Home Assistant `last_reported` time passed ZEAL's one-hour stale
threshold and then remained unhealthy through the five-minute notification
debounce. Check that entity in Developer Tools and download diagnostics. The
notification also says whether another usable TRV or sensor still covers the
room, and it dismisses automatically after a fresh usable state arrives.

## One Zone/Floor temporarily disappears from Schedule

Update to the current candidate. Entering Schedule now refreshes the complete
saved configuration, and Setup waits longer for a slow config-entry reload.
If it happens again, do not recreate the zone: reload the ZEAL page and attach
redacted diagnostics with the exact save sequence to the issue report.

## Enable diagnostic logging

Use **Settings → Devices & Services → ZEAL HVAC System → Enable debug logging**
for a temporary trace. Reproduce the problem, then disable logging and download
diagnostics. The configuration and audit downloads under **ZEAL → Setup** are
separate and useful for comparing saved intent with target applications.

Before sharing any export, review room names, zone names and entity IDs for
personal information. Never publish Home Assistant credentials or access
tokens.

## Report an issue

Open an issue at <https://github.com/Buster1959/ZEAL/issues> with the ZEAL
version, Home Assistant version, expected result, actual result and the smallest
reproducible steps. Attach redacted diagnostics/audit data only when useful.
