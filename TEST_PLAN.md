# ZEAL HVAC System — Test Plan

*For the current V1 feature build: minimal Config Flow, HTML Overview/Setup
panel, Coordinator control loop and scheduler backend. Written to be usable
as-is by anyone testing this from a fresh HA install — every step names the
exact screen, tab, and field.*

> **Fastest option for verifying the Coordinator's own logic:**
> `tests/` has an automated pytest suite (118 collected cases, runs in seconds)
> second) covering the demand-calculation combination matrix directly —
> see `tests/README.md`. This test plan is for everything that suite
> *can't* cover: browser rendering and interactions, real (or dummy)
> hardware behaving as expected, and anything end-to-end. Use both —
> the automated suite for "did I break the logic," this document for
> "does it actually work against something real."

## 0. Scope and known gaps — read first

- **Heat source and re-enable delay are setup fields.** The heat-source choice
  supplies a recommendation; the stored delay remains user-editable. Future
  thermal learning is still outside V1.
- **The ZEAL Overview is now the persistent configuration summary.** It shows
  zones, Areas/rooms, heat source, actuator, delay and equipment counts. The
  standard diagnostics download remains useful for portable troubleshooting.
- **Scheduling, Quick Change, downloads and Away mode are built.** Their pure,
  runtime, security and persistence contracts have automated coverage; §5 adds
  the essential browser/live checks.

## 1. Where to see what you've configured

**A. ZEAL Overview and Setup.** Open **ZEAL** from the Home Assistant sidebar,
or choose **Configure** on the integration card. **Overview** is the glanceable
saved summary. **Setup** displays every editable field and pre-fills it from the
current configuration.

**B. Download diagnostics.** `Settings → Devices & Services → ZEAL HVAC System
→ ⋮ → Download diagnostics` produces a structured snapshot including live
entity state for troubleshooting.

**C. Devices & Entities (integration-created entities only).**
`Settings → Devices & Services → Entities`, filtered to this integration,
shows the two entities it creates *per zone*: the manual override switch
and the demand sensor. It does **not** show your own TRVs/sensors — those
remain listed under whichever integration actually owns them (Zigbee2MQTT,
deCONZ, etc.), not under ZEAL. Each zone also appears as its own **Device**
(`Settings → Devices & Services → Devices`, filtered to this integration)
containing those same two entities.

## 2. Build a fully virtual test rig (UI only, no YAML, no real hardware)

> **Faster alternative for a full multi-zone/multi-room rig:**
> `test_fixtures/dev_environment.yaml` (+ its companion `SETUP.md`) gives a
> deterministic, pre-built 2-zone/6-room dummy rig in one file — the same
> shape this section builds by hand, but guaranteed identical every time
> it's used, which matters if more than one person (or session) is testing
> against it. This section's UI-only walkthrough is still the right choice
> if you specifically want zero YAML edits or just need one quick isolated
> room to test against.

This gives you one dummy "room" — a TRV with an adjustable setpoint and a
temperature sensor with an adjustable reading — plus a dedicated dummy
switch to act as the zone's heating actuator. Confirmed buildable entirely
from Settings screens on current HA (2026.8.x); no `configuration.yaml`
editing required anywhere in this section.

### 2.1 Dummy room temperature sensor

1. **Settings → Devices & Services → Helpers tab → + Create Helper → Number.**
   - Name: `Test Room Temp` (entity becomes `number.test_room_temp`)
   - Minimum: `0`, Maximum: `35`, Step: `0.1`, Unit of measurement: `°C`
   - This is the slider you'll actually drag during testing.
2. **Helpers tab → + Create Helper → Template → Template a sensor.**
   - Name: `Test Room Sensor` (entity becomes `sensor.test_room_sensor`)
   - State template: `{{ states('number.test_room_temp') }}`
   - Device class: **Temperature**
   - Unit of measurement: `°C`
   - This is the entity ZEAL will actually read — it mirrors whatever the
     Number helper above is set to, live.

### 2.2 Dummy TRV (a real `climate` entity with an adjustable setpoint)

1. **Helpers tab → + Create Helper → Template → Template a switch** (this
   is a separate wizard from the sensor one, still under Template).
   - Name: `Test TRV Internal Heater` (entity becomes
     `switch.test_trv_internal_heater`)
   - Leave the **state template field blank.** Leaving it empty puts the
     switch in *optimistic* mode — it just remembers whatever you last set
     it to, with no dependency on anything else. This entity is never
     looked at directly during testing; Generic Thermostat below just
     needs *some* switch to nominally control.
2. **Settings → Devices & Services → Add Integration → search "Generic
   Thermostat".**
   - Name: `Test TRV`
   - Heater switch: `switch.test_trv_internal_heater` (from step 1)
   - Target sensor: `sensor.test_room_sensor` (from §2.1)
   - Leave other fields at their defaults.
   - This creates `climate.test_trv` — a real climate entity whose target
     temperature you can set from its thermostat card, exactly like a real
     TRV. ZEAL reads this entity's `temperature` attribute as the room's
     setpoint.

### 2.3 Dummy zone actuator switch

1. **Helpers tab → + Create Helper → Template → Template a switch.**
   - Name: `Test Zone Switch` (entity becomes `switch.test_zone_switch`)
   - Leave the state template blank (optimistic, as in §2.2 step 1).
   - **This is the switch you'll actually be watching during the test** —
     do not confuse it with the internal one from §2.2, which exists only
     to satisfy Generic Thermostat's setup requirements and has no bearing
     on the test itself.

### 2.4 Put the dummy TRV and sensor in an Area

1. **Settings → Areas & Zones** — create an Area if you don't already have
   a spare one, e.g. `Test Room`.
2. For **both** `climate.test_trv` and `sensor.test_room_sensor`: open the
   entity's settings (gear icon on its more-info dialog, or via
   `Settings → Devices & Services → Entities`, click the entity, then the
   cog) and assign it to the `Test Room` Area. This is required — ZEAL's
   ZEAL Setup lists TRVs/sensors *by Area*, so anything not
   assigned to an Area won't show up as a pick.

## 3. Configure a test zone in ZEAL

1. `Settings → Devices & Services → Add Integration → ZEAL` (or "ASHP Zone
   Control" if not yet renamed). Give the instance any name and finish.
2. Open **ZEAL** from the sidebar and select **Setup**.
3. Select **+ Add zone** and name it `Test Zone`.
4. Set **Heating actuator switch** to `switch.test_zone_switch` (§2.3) —
   **not** the internal switch from §2.2.
5. Set **Heat source** to any suitable value (e.g. "Other / not sure").
   Confirm the recommendation shown below it is 300s for ASHP/Other, 120s
   for a modulating boiler or 60s for a non-condensing boiler.
6. Under **Rooms**, select `Test Room` from **+ Add Area as room**.
7. **Re-enable delay** — accept the suggested value, or lower it (e.g. to
   `15`) to make §4 step 5's re-enable-delay check faster to observe
   without editing `const.py`.
8. In the Test Room card, select `climate.test_trv` under physical climate
   thermostats/TRVs and `sensor.test_room_sensor` under temperature sensors.
   Leave **Room is active** on.
9. Select **Save setup**. Wait for the saved/reloaded confirmation, then return
   to **Overview** and confirm it shows Test Zone, the actuator, heat source,
   delay and Test Room with one TRV and one sensor.

## 4. Run the actual demand test

1. Open `climate.test_trv`'s more-info dialog (thermostat card) and set
   its target temperature to, say, **20°C**.
2. Open `number.test_room_temp` and set it **above** 20°C — e.g. 22.
   - Expected: `sensor.test_room_sensor` follows to 22 within a second or
     two (it's a live template). The Coordinator is watching that sensor
     directly (`async_track_state_change_event`), so it should re-evaluate
     almost immediately rather than waiting for the 60-second poll.
   - Expected result: `switch.test_zone_switch` is (or goes/stays) **off**
     — room is warmer than the setpoint, no demand.
3. Set `number.test_room_temp` **below** 20°C — e.g. 18.
   - Expected: within a few seconds, `switch.test_zone_switch` turns **on**.
   - Check the zone's **Demand sensor** (`Settings → Devices & Services →
     Entities`, filter to this integration, or via the zone's Device page)
     — its state should read `Demand`, with an attribute listing something
     like `Test Room: Set 20.0°C, Room 18.0°C (Δ 2.0°C)`.
4. Set `number.test_room_temp` back **above** 20°C.
   - Expected: `switch.test_zone_switch` turns **off**, Demand sensor
     reads `No demand`.
5. **Re-enable delay check.** Immediately after step 4 (switch just went
   off), push `number.test_room_temp` back below 20°C again.
   - Expected: the switch does **not** turn back on immediately — it
     should stay off for however long you set in §3 step 7 (e.g. 15
     seconds if you lowered it for faster testing, or the full suggested
     default if you left it) before turning on, even though the room is
     genuinely cold. This is the anti-short-cycling behaviour ported from
     the old `ashp_controller.py`, not a bug. If you didn't lower the
     delay in §3, this step will take longer to observe — open
     **ZEAL → Setup** and lower the re-enable delay there rather
     than editing any code.
6. **Manual override check.** With the room cold (demand present, switch
   on), find the zone's **Manual override switch** (same Entities/Device
   screen as the Demand sensor) and turn it **on**.
   - Expected: `switch.test_zone_switch` is left exactly as it was — the
     Coordinator should stop acting on it entirely while the override is
     on, even as you move `number.test_room_temp` up and down. Turn the
     override back off afterward and confirm normal control resumes.

## 5. Check Schedule, Quick Change and Away mode

1. Open **ZEAL → Schedule**, select the test room, add at least two changes a
   few minutes apart and save. Confirm the ZEAL room thermostat and dummy TRV
   receive each target at the displayed time.
2. Open **Quick Change**, select the test room, apply an exact target for two
   hours, then cancel it. Confirm the room first uses the hold and then returns
   to its current scheduled target.
3. In **Setup → Away mode**, choose **Start and end date/time** with a start a
   few minutes ahead, an end a few minutes after that and a distinctive safe
   target such as 12°C. Save. Confirm normal control continues before the start,
   the target changes at the start and normal control resumes at the end.
4. Repeat with **Home Assistant Calendar** using a dedicated short test event.
   Confirm Away is active only while the calendar entity is `on`.
5. During either active test, confirm Quick Change is disabled and select
   **End Away now**. Confirm control resumes immediately without waiting for the
   event/end time.
6. Optional restart check: restart Home Assistant during an active date period
   or calendar event. Confirm the Away banner and target are restored after
   startup.
7. Download the configuration and audit trail from Setup. Confirm the Away
   settings and `away_mode_activated` / `away_mode_ended` application causes
   are present and no credentials or tokens appear.

## 6. Cleanup

Once satisfied, remove the test zone via **ZEAL → Setup → Remove zone →
Save setup**, then delete the four Helpers (`Test Room Temp`, `Test Room
Sensor`, `Test TRV Internal Heater`, `Test Zone Switch`) and the Generic
Thermostat integration instance (`Test TRV`) from their respective
Settings screens. None of this leaves anything behind in `configuration.yaml`
since it was all created via UI helpers/config flows.

## 7. Open items this test plan does not cover

- Multiple TRVs/sensors in one room (average sensor / highest-setpoint
  logic) — repeat §2 twice more with a second dummy TRV/sensor pair in the
  same Area, and verify the aggregation behaves as described in the
  project doc §3.1.
- Multiple zones sharing vs. not sharing hardware, per your actual house
  layout (single-pump-two-zones, dual-pump, hotel-per-level) — this test
  plan builds one isolated zone; a second pass with two zones and two
  distinct dummy switches would confirm they don't interfere with each
  other.
