# ZEAL Learning Roadmap

ZEAL Learning is planned for the next major version after V1. It is divided
into two explainable, independently testable workstreams. Neither workstream may
silently alter the saved weekly schedule.

## 1. ZEAL Learning — Schedule Adaptation

Schedule Adaptation learns from repeated user intent. It records source-aware
setpoint events from Home Assistant/canonical thermostats, physical TRVs and
Quick Change, always retaining the scheduled baseline that was overridden.

A candidate pattern is a configurable number of similar manual changes—for
example, three changes—within a comparable time window across a configurable
number of days. Once the evidence threshold is met, ZEAL creates a proposal
showing:

- the room and supporting audit events;
- the affected days and time window;
- the existing schedule time and setpoint;
- the proposed schedule edit and evidence count/confidence;
- Accept, Edit, Dismiss and Snooze actions.

Only Accept or Edit followed by confirmation writes a new schedule revision
through the existing validated API. Proposal creation and disposition are
audited, allowing ZEAL to suppress a dismissed pattern until materially new
evidence exists.

## 2. ZEAL Learning — Room Thermal Response

Room Thermal Response learns how each room and its surrounding building fabric
respond to heating under different outdoor conditions. Its first user-facing
application is **optimum start**: predicting when heating should begin so a room
reaches its scheduled target at the scheduled time.

### Weather and outdoor-temperature sources

Setup should select entities through Home Assistant's common interfaces rather
than hard-code provider names:

1. **Observed outdoor temperature** — preferably a local outdoor temperature
   sensor; otherwise the current temperature of a compatible `weather` entity.
2. **Optional forecast weather entity** — a `weather` entity that supports
   hourly forecasts through `weather.get_forecasts`.

Actual observed outdoor temperature trains the model. Forecast temperature is
used only when predicting a future heating start. Forecast values must not be
stored as if they were observations.

Initial compatibility testing should cover:

- [Met Office](https://www.home-assistant.io/integrations/metoffice/) — official
  Home Assistant integration with current conditions and hourly forecasts;
- [Open-Meteo](https://www.home-assistant.io/integrations/open_meteo/) — official
  integration with no account/API key requirement and hourly forecasts;
- [Pirate Weather](https://github.com/Pirate-Weather/pirate-weather-ha) — custom
  Home Assistant integration exposing weather data through the common entity
  model.

These are a compatibility test matrix, not a permanent allow-list. A later
provider should work without ZEAL-specific code when it exposes the required
standard entity attributes and hourly forecast capability. ZEAL should validate
capabilities when the entity is selected and clearly report missing or stale
data.

Home Assistant's current weather contract and forecast action are documented at
[Weather](https://www.home-assistant.io/integrations/weather/).

### Initial thermal model

Start with an explainable first-order resistance/capacitance model rather than
PID:

```text
C × dTi/dt = Qheat − H × (Ti − To) + disturbances
```

Where:

- `Ti` is room temperature;
- `To` is observed outdoor temperature;
- `Qheat` is effective heat input;
- `C` is effective room/building thermal mass;
- `H` is the room heat-loss coefficient;
- `C/H` is the thermal time constant;
- disturbances include solar gain, occupants, appliances and open windows.

For recorded samples, ZEAL can fit the discrete relationship:

```text
ΔTi / Δt = a × Qheat − b × (Ti − To) + error
```

This supports understandable estimates such as heat-up rate in °C/hour at a
given outdoor temperature, response delay, cooldown rate and predicted time to
target. Model parameters and confidence are per room; one room's result must not
be applied to another room merely because both share a zone.

PID is not the initial learning model. PID controls a continuously adjustable
output in real time and may later suit proportional valve position, fan speed or
heat-demand modulation. With V1's room setpoints, TRVs and mostly binary zone
actuators, a second PID could conflict with the TRVs or heat source's own
controller. Optimum-start prediction should come first.

### Observation record

Each sample or heating episode should retain enough provenance to reproduce the
result:

- room ID, timestamp and sample interval;
- room temperature at the start/end and its rate of change;
- observed outdoor temperature and source entity;
- scheduled and effective setpoint plus control source;
- room demand, zone actuator and thermostat/TRV state;
- heat-source type and, where available, flow temperature or modulation;
- optional valve position, window/door state, occupancy and solar/cloud data;
- sensor availability, staleness and exclusion reason;
- model version and the parameters/confidence produced from the observation.

### Data-quality exclusions

ZEAL should reject or down-weight episodes affected by unavailable/stale
sensors, an open window, an interrupted heating run, manual changes during the
episode, an unobserved secondary heat source or implausible temperature jumps.
Solar gain and occupancy should initially reduce confidence unless corresponding
data is available; they must not be mislabelled as radiator performance.

### User experience

Overview should progress from observation to an explainable recommendation:

```text
Thermal model: Learning — 12 valid heating cycles
```

then, for example:

```text
Thermal model: Established
Estimated heat-up rate: 0.62°C/hour at 5°C outside
Estimated start for 20°C by 07:00: 05:48
Confidence: Medium
```

ZEAL should first offer an optimum-start recommendation for review. Enabling
automatic optimum start must be a separate, explicit user choice after the room
model reaches a defined confidence threshold. The original scheduled target
time and temperature remain unchanged; optimum start changes only when heating
begins in preparation for that target.

### Acceptance gates

- Deterministic synthetic-room tests recover known thermal parameters within a
  defined tolerance.
- Provider contract tests cover Met Office, Open-Meteo and Pirate Weather-shaped
  weather entities without provider-specific control paths.
- Forecast values and actual observations remain distinguishable in storage.
- Restarts, missing forecasts and stale outdoor readings fail safely without
  losing the existing schedule.
- Model recommendations include evidence, model version and confidence.
- No schedule or heating start is changed without the required user approval.
- Learning history has bounded retention, export/redaction rules and an explicit
  occupancy-privacy warning.

## Sequencing

1. Ship and validate V1 without learning dependencies.
2. Add the source-aware event audit required by Schedule Adaptation.
3. Build Schedule Adaptation proposals and approval workflow.
4. Add outdoor-source selection and observation-only thermal data collection.
5. Validate per-room models offline before showing recommendations.
6. Release advisory optimum start.
7. Consider explicitly enabled automatic optimum start.
8. Consider PID only for future hardware with a suitable proportional output.
