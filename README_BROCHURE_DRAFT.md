<p align="center">
  <img src="custom_components/zeal/brand/icon.png" width="112" height="112" alt="ZEAL icon">
</p>

<h1 align="center">ZEAL</h1>
<p align="center"><strong>SMARTER HEATING. COOLER THINKING.</strong></p>

<h2 align="center">One intelligent place for the heating in your whole home</h2>

<p align="center">
  <strong>Zoned, Efficient, Adaptive, Learning.</strong><br>
  ZEAL brings heating control, room scheduling, temporary changes and clear
  demand information together inside Home Assistant.
</p>

<p align="center">
  <a href="#see-zeal-in-action">See ZEAL in action</a> ·
  <a href="#install-zeal">Install with HACS</a> ·
  <a href="../../wiki">Read the user guide</a>
</p>

> **Pre-V1 preview.** ZEAL is undergoing live testing and is not yet the
> production `1.0.0` release. Its core heating controls and Schedule Adaptation
> are implemented; Room Thermal Response and one-click History links remain in
> development. Test releases with dummy or spare equipment before unattended use.

## Heating control without the patchwork

Many smart-heating installations grow into a collection of thermostats,
schedules, helpers and automations. ZEAL provides one guided Home Assistant
integration that understands the relationship between the heat source, each
heating zone and every room within it.

| One ZEAL integration | What it gives you |
|---|---|
| **Universal zone control** | Coordinate rooms and zone actuators across air-source heat pumps, modulating or conventional boilers, and other hydronic heat sources. |
| **Guided setup** | Build zones from familiar Home Assistant Areas, then select the actuator, TRVs and temperature sensors already in your home. |
| **Visual scheduling** | Shape a seven-day temperature schedule for every room with graphical timelines and simple copy controls. |
| **Demand at a glance** | See which rooms need heat, which are satisfied, and whether the zone actuator is actually running. |
| **Everyday overrides** | Make a Quick Change for selected rooms or set Away mode without damaging the saved weekly schedule. |
| **Selectable learning** | Let ZEAL observe repeated household choices and offer reviewable Schedule Adaptation suggestions. Learning remains under administrator control. |
| **Native history** | Record room demand alongside temperature, setpoint and actuator state for inspection with Home Assistant's own History tools. |

## Clear answers, room by room

The Overview separates two questions that are often confused:

- **Does a room want heat?** ZEAL compares its effective setpoint with its
  measured temperature and accounts for room-level exclusions such as an open
  window or door.
- **Is the heating actuator on?** ZEAL shows the real Home Assistant switch
  state independently, so a re-enable delay, manual override or safety hold is
  visible rather than disguised as “no demand”.

That makes the system useful at a glance and useful when something does not
behave as expected.

## See ZEAL in action

### Set up the home you actually have

Create practical zones, attach rooms, and choose the existing Home Assistant
equipment for each room. ZEAL supports multiple TRVs and temperature sensors
per room and creates one clear room thermostat as the shared target.

![ZEAL guided zone and room setup](docs/images/zeal-zone-and-room-setup-desktop.png)

### Draw the week, instead of programming it

Every room has a seven-day graphical schedule. Adjust times and temperatures,
copy a useful pattern to selected days or rooms, and keep the final decision in
human hands.

![ZEAL graphical seven-day room schedule](docs/images/zeal-seven-day-schedule-desktop.png)

### Change the temperature without changing the plan

Quick Change applies a temporary adjustment to one room, a zone, a chosen
group, or the whole home. Choose two hours, four hours or until the next
scheduled change; the weekly schedule stays intact.

![ZEAL Quick Change controls](docs/images/zeal-quick-change-desktop.png)

### Leave home without rebuilding every schedule

Away mode can use an exact date range or follow a Home Assistant calendar,
then automatically returns control to the normal schedule.

![ZEAL Away mode with an exact date range](docs/images/zeal-away-date-range-desktop.png)

## Learning that remains accountable

Learning in ZEAL is optional. An administrator enables it, and schedule changes
are never silently committed.

### Schedule Adaptation — implemented for testing

ZEAL can identify repeated manual thermostat choices across distinct days and
turn them into a clear recommendation. An authorised person can accept, edit,
snooze or dismiss it. The evidence and outcome remain reviewable, while the
saved schedule changes only after explicit approval.

### Room Thermal Response — in development

The next learning module is designed to learn how each room warms and cools in
different outside conditions. Its first practical goal is optimum start: begin
heating early enough to reach the existing scheduled temperature at the
existing scheduled time, without moving that target or hiding the reasoning.

Thermal Response is a continuous system function, selectable by an
administrator, with Home Assistant storage and clear confidence and hold
information rather than a black-box promise.

## Designed to work with Home Assistant

- No separate web server or AppDaemon installation.
- No custom dashboard card required for the main ZEAL experience.
- Uses Home Assistant Areas and existing climate, temperature, contact-sensor
  and switch entities.
- Uses Home Assistant permissions: Overview for signed-in users; Setup for
  administrators; Schedule, Learning and Quick Change may be delegated.
- Uses Home Assistant's own persistent notifications, diagnostics, storage and
  Recorder history instead of duplicating platform services.
- Protects real heating equipment with actuator re-enable delays, unavailable
  device handling, setpoint bounds and closed-valve pump safeguards.

## Install ZEAL

[![Open ZEAL in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Buster1959&repository=ZEAL&category=integration)

ZEAL is currently installed as a HACS custom repository:

1. Open HACS and select **Custom repositories**.
2. Add `https://github.com/Buster1959/ZEAL` as an **Integration**.
3. Download **ZEAL HVAC System**, restart Home Assistant, then add ZEAL from
   **Settings → Devices & Services → Add Integration**.

For current setup instructions, permissions, testing guidance and
troubleshooting, use the [ZEAL wiki](../../wiki).

## Project status

ZEAL is an actively tested pre-V1 project. The detailed architecture, safety
contracts, test evidence and engineering decisions remain in this repository;
the wiki is the maintained source for user instructions.

- [Architecture](docs/ARCHITECTURE.md)
- [Learning roadmap](docs/LEARNING_ROADMAP.md)
- [Live test plan](TEST_PLAN.md)
- [Draft V1 release notes](docs/RELEASE_NOTES_V1_DRAFT.md)

## Licence

ZEAL is source-available under the
[PolyForm Shield License 1.0.0](LICENSE). You may use, study and modify it for
permitted purposes; review the licence before redistribution or commercial use.

<p align="center"><strong>ZEAL</strong><br><em>Zoned, Efficient, Adaptive, Learning.</em></p>
