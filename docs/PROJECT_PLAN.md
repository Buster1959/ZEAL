# ZEAL V1 Block Plan

Each block is completed, tested, documented and committed before work begins on
the next block. The completed V1 candidate was fast-forwarded to `main`; live
regression fixes are prepared on short-lived branches and retested before merge.

## Block 0 — Repository review and architecture boundary

- Audit code, tests, setup, persistence, releases, repository docs and Wiki.
- Record the independent-integration boundary with Visual Climate Scheduler.
- Record the competing thermostat-setpoint scheduler warning.

Status: complete (`docs/ZEAL_V1_REVIEW.md`).

## Block 1 — Truthful baseline

- Reconcile manifest, repository and documentation versions.
- Consolidate every current Coordinator test under `tests/`.
- Remove test modules from production integration code.
- Establish repeatable local test and compile commands.

Acceptance: one discoverable baseline suite covers all current ZEAL control and
safety behaviour; version statements agree.

Status: complete. The consolidated suite passes 38/38 cases, including
setpoint clamping, stale-reading rejection and debounced offline/recovery
notifications.

## Block 2 — ZEAL-owned scheduler model

- Transplant and namespace the VCS schedule model, validation, migration,
  deterministic engine, copy semantics and override calculations.
- Bind schedule records to stable ZEAL room IDs, not physical TRV entity IDs.
- Add versioned schedule storage independent of Coordinator runtime state.

Acceptance: pure scheduler tests pass without Home Assistant runtime objects.

Status: complete. ZEAL now owns its scheduler model, migration, engine, editor
copy semantics, room reconciliation, temporary-override calculations and a
separate versioned Store adapter. The 25 scheduler cases pass; the complete
suite passes 63/63.

## Block 3 — ZEAL scheduler adapter and runtime

- Map zones/rooms to canonical ZEAL room thermostats.
- Apply schedule targets through the existing ZEAL room setpoint path.
- Add startup reconciliation, nearest-transition timing and unavailable-room
  handling.
- Ensure physical TRVs are never independently scheduled.

Acceptance: service/runtime tests prove only canonical ZEAL room targets are
changed and existing Coordinator safety behaviour remains unchanged.

Status: complete. Startup loads and reconciles the separate schedule document,
the runtime applies active periods through stable room IDs and the Coordinator's
canonical room-target boundary, missing room thermostats retry safely, and only
the nearest transition is timed. The complete suite passes 73/73.

## Block 4 — Configuration and WebSocket boundary

- Add validated admin-only read/write APIs for ZEAL configuration, schedules,
  hierarchy, Quick Change, downloads and audit.
- Preserve versioned persistence and reload safety.

Acceptance: malformed, unauthorized and conflicting updates fail safely; valid
updates survive reloads.

Status: complete. The API validates hierarchy against Home Assistant registries,
uses deterministic revision tokens to reject stale writes, updates schedule
runtime immediately, survives hierarchy reloads, and exposes bounded audit and
configuration export documents. Admin/read-only WebSocket behavior is tested.
The complete suite passes 94/94.

## Block 5 — HTML Overview and Setup

- Add a versioned admin-only ZEAL panel using the established VCS visual system.
- Keep the initial Config Flow minimal and replace the existing multi-page
  Configure experience with the ZEAL panel once that route exists.
- Build Overview and Setup views for zones, Areas, rooms, switches, heat source,
  re-enable delay, TRVs, sensors and active state.
- Include the competing-setpoint-scheduler safety warning.

Acceptance: a fresh installation can be fully configured without the existing
multi-page Options Flow and existing configuration can be modified safely.

Status: complete. ZEAL now registers a versioned admin-only Home Assistant panel
as both a sidebar and integration configuration route. Overview summarizes the
configured heating system; Setup edits the complete zone/Area/room hierarchy,
Area-scoped physical TRVs and sensors, active state, heat source, actuator and
re-enable delay through the Block 4 validated API. Optimistic concurrency,
reload recovery, responsive layouts and the competing-scheduler warning are
included. The former multi-page Options Flow has been retired without changing
stored configuration. Canonical ZEAL scheduling thermostats and physical room
equipment use separate registry-owner-filtered catalogs, preventing a ZEAL
thermostat from being selected as its own physical TRV. The complete suite
passes 98/98.

## Block 6 — Visual scheduling

- Adapt the seven-day timeline editor to ZEAL rooms and zone navigation.
- Preserve exact time/setpoint entry, day application, cross-midnight carry and
  one-time room schedule copying.
- Provide responsive desktop/tablet/mobile layouts.

Acceptance: saved schedules execute exactly as displayed and remain independent
between rooms and days.

Status: complete. The admin-only Schedule page navigates the existing
Zone/Floor and room hierarchy, edits all seven days with draggable points or
exact fields, displays cross-midnight carry, applies one source day locally,
and saves or copies through conflict-protected APIs. Schedules target canonical
ZEAL room thermostats only; copying preserves every destination's identity and
physical equipment. Desktop, tablet and mobile layouts are included. The
complete suite passes 100/100.

## Block 7 — Quick Change, downloads and audit

- Add temporary per-room, selected-room and whole-house holds.
- Add JSON configuration export and bounded persistent application audit.
- Record causes, targets and outcomes without logging secrets.

Acceptance: holds never edit saved schedules; downloads are complete and
restart-safe; audit retention is bounded.

Status: complete. Quick Change supports individual rooms, complete Zone/Floor
groups, arbitrary selections and the whole house, with relative or exact
targets lasting two hours, four hours or until the next schedule transition.
Holds remain transient and never mutate weekly schedules. Setup provides fresh
JSON configuration and audit downloads; audit outcomes persist separately,
survive a new runtime instance, contain no secrets and retain only the newest
500 records. The complete suite passes 102/102.

## Block 8 — Away mode and precedence

- Add a mutually exclusive calendar-driven or start/end global Away mode and
  temperature.
- Define and test precedence among away mode, temporary holds, schedules,
  manual thermostat changes and zone manual override.
- Reconcile correctly when modes begin, end or Home Assistant restarts.

Acceptance: every precedence transition has automated coverage and no unsafe
setpoint can bypass ZEAL's clamp.

Status: complete. Setup provides Off, Home Assistant Calendar and one exact
start/end period as mutually exclusive activation sources, with a global 12°C
default target for active rooms only. Calendar changes and date boundaries are
tracked without polling; persisted UTC timestamps are interpreted from Home
Assistant's configured time zone and reconciled on restart. The panel exposes
live/waiting/scheduled/finished/unavailable status and blocks competing Quick
Change requests while Away is active. Tests cover activation/end, active-room
scope, existing-hold pause/resume/expiry, manual-change reassertion, normal
manual-change persistence, restart reconciliation and the unchanged Zone Manual
Override actuator authority. The complete suite passes 118/118.

## Block 9 — Documentation, Wiki, languages and HACS packaging

- Standardize repository and Wiki structure with VCS.
- Add installation, setup, scheduling, mobile, downloads, troubleshooting,
  architecture, data model, decisions, release notes and acceptance tests.
- Add privacy-reviewed screenshots, translations, `hacs.json`, HACS validation
  and Hassfest workflows.

Acceptance: repository and Wiki agree, technical validation passes,
custom-repository installation is documented, and documentation contains no
personal installation details.

Status: in progress. HACS metadata, HACS/Hassfest workflows, ten setup-flow
language files, repository/Wiki user and technical guides, release draft,
privacy rules and UI acceptance tests are implemented. The complete automated
suite passes and Hassfest passes. Privacy-reviewed ZEAL desktop
screenshots from the generic test installation are now documented; the mobile
captures remain a Block 9 gate.
HACS currently rejects the existing PolyForm Shield licence because it cannot
identify it as an OSI-approved licence. The project owner has chosen to keep
PolyForm Shield and distribute ZEAL through HACS as a custom repository. The
licence result is therefore expected and is not an application-code or V1
release failure.

## Block 10 — V1 validation and release preparation

- Run the full automated suite and live Home Assistant acceptance plan.
- Verify restarts, unavailable devices, multiple zones, multiple TRVs/sensors,
  persistence and 24-hour schedule/audit behaviour.
- Prepare the V1 manifest, release notes and reviewable merge to `main`.

Acceptance: all gates pass and no required V1 work remains.

Status: in progress on `main`. Automated tests, compilation, frontend syntax,
JSON/YAML, repository hygiene and release-metadata contracts passed for the
initial candidate. The live acceptance matrix is recorded in
`docs/V1_ACCEPTANCE_RECORD.md`; regression feedback is being fixed and affected
checks will be repeated. Manifest `1.0.0`, tag and GitHub release remain gated
on the pending live checks and mobile screenshots. The release will be
distributed through the documented custom-HACS route.

## Baseline close-down blocks before Room Thermal Response

The remaining work is ordered by the owner's current importance list. Complete
these blocks in sequence unless a release-critical defect interrupts them.

### Close-down Block 1 — documentation source of truth

Issue: [#8 Block 1: Discuss README and wiki source-of-truth boundary](https://github.com/Buster1959/ZEAL/issues/8)

Priority: **1 — highest**. Decide how much detail belongs in README, the GitHub
wiki and repository documentation. Preserve essential installation, safety and
offline material while giving every subject one maintained source of truth.

Status: **complete**. Wiki commit `deee6e2` establishes the ownership map and
expands the maintained user guide/troubleshooting pages. Repository commit
`8184962` makes README's active path concise, points current user guidance to
the wiki and labels the full repository guide copies/README detail as archived
cross-check snapshots. No text was deleted during the transition.

Acceptance: an explicit document ownership map exists, duplicate material is
removed or reduced to links, and no user guidance is lost during migration.

### Close-down Block 2 — multi-module Learning interface

Issue: [#7 Block 2: Structure Learning as multiple modules](https://github.com/Buster1959/ZEAL/issues/7)

Priority: **2**. Agree the navigation and information architecture for Schedule
Adaptation and Room Thermal Response before adding the second Learning module.

Agreed design: Schedule Adaptation is enabled Yes/No by an administrator
in Setup; Setup provides compact administrator progress. An actionable proposal
reveals **Schedule Updates** to administrators and Schedule/Learning-authorised
users and hides from standard users when no action remains. Thermal Response is
entirely administrator-only: its persistent Learning page combines room status,
confidence, evidence and response history in one graph view; Setup owns initial
settings plus confirmed per-room/all-room resets. Administrator UI uses readable
names, diagnostics are pseudonymised, and resets never alter schedules or other
configuration.

Acceptance: module overview, evidence/status, recommendations, history, privacy,
reset controls and the Setup/Learning boundary are specified before UI code.

Status: **complete**. Design decisions are recorded in
`docs/LEARNING_ROADMAP.md` and `docs/DECISIONS.md`.

### Close-down Block 3 — Learning documentation evidence

Issue: [#9 Block 3: Complete Learning guide screenshots](https://github.com/Buster1959/ZEAL/issues/9)

Priority: **3**. The guide and troubleshooting are complete in `8e9617b`.
Allow the holiday automation to create genuine Learning evidence, then capture
the four privacy-reviewed screenshots without forging production events.

Acceptance: settings, evidence progress, an actionable suggestion and proposal
history/Revert are illustrated using privacy-reviewed captures.

### Close-down Block 4 — Thermal Store volume and retention

Issue: [#6 Block 4: Define Thermal Store volume and retention](https://github.com/Buster1959/ZEAL/issues/6)

Priority: **4**. Define observation cadence, episode boundaries, retention,
compaction, migration, restart deduplication, reset/deletion and export privacy.
Use bounded, versioned Home Assistant Stores; do not introduce MariaDB or a
separate SQLite database.

Acceptance: the persistence and privacy contract is agreed before observation
collection code is written.

Agreed contract: five-minute relevant-period samples; per-room versioned Store
documents; 30 days/2,000 detailed samples; 365 days/750 episode summaries;
15-minute active checkpoints; stable-ID restart deduplication; and
pseudonymised ordinary diagnostics. Disabling asks whether to keep data
(default), delete it permanently, or cancel. Reset/deletion never changes
configuration, schedules or overrides.

Status: **complete**. The persistence contract is recorded in
`docs/DATA_MODEL.md` and `docs/LEARNING_ROADMAP.md` before implementation.

### Completed baseline corrections

Issues [#1](https://github.com/Buster1959/ZEAL/issues/1),
[#2](https://github.com/Buster1959/ZEAL/issues/2),
[#3](https://github.com/Buster1959/ZEAL/issues/3),
[#4](https://github.com/Buster1959/ZEAL/issues/4) and
[#10](https://github.com/Buster1959/ZEAL/issues/10) are fixed and closed. Their
commit evidence remains on each issue. ZEAL Flow work belongs to its independent
repository/project and is not part of this close-down plan.

## ZEAL Learning — Schedule Adaptation

The first complete vertical pipeline is implemented behind an administrator
opt-in while V1 live regression work continues. It uses a separate versioned
store, so it does not change the established scheduler audit schema.

The user experience analyses habits, proposes an optimisation and applies it
only after acceptance. ZEAL includes an inspectable evidence trail, exact
schedule diff, optimistic revision check and auditable revert. The detailed
specification is in `docs/LEARNING_ROADMAP.md`.

Implementation is one complete vertical pipeline from capture and classification
through detection, recommendation, confirmation, commit and revert—not an
observation-only release. Stable households
may not produce enough natural changes for timely passive validation, so
synthetic dated event streams must exercise the actual production classifier,
proposal engine, authorisation and revision-checked commit path. Learning is
disabled by default; automatic detection can create advice, while only explicit
user confirmation can mutate a schedule.

- Extend the audit from canonical application outcomes to source-aware user
  intent: weekly schedule, Home Assistant/canonical thermostat, physical TRV,
  Quick Change, Away and later ZEAL suggestions.
- Retain the scheduled baseline, requested/effective target, timestamp, room,
  source, temporary duration/expiry and outcome needed to explain each event.
- Detect repeated manual changes in comparable time windows. Threshold count,
  time-window tolerance and observation period must be configurable; an initial
  example is three similar changes within the same part of the day across a
  defined number of days.
- Assign every event to one immutable room/weekday/period/revision snapshot.
  Adjacent periods remain separate and ambiguous transition-boundary events are
  excluded. Comparable evidence may cross weekdays, but an accepted proposal
  changes only the weekday on which it was raised.
- Create a reviewable proposal containing the supporting events, current
  schedule period and proposed replacement target/time.
- Offer Accept, Edit, Dismiss and Snooze. Accepting writes through the normal
  validated schedule API and creates a new revision; no learned change is ever
  auto-applied.
- Audit proposal creation and user disposition so dismissed suggestions are not
  repeatedly presented without materially new evidence.
- Keep broader day copying in the ordinary Schedule page; Learning proposals
  include an **Open Schedule** handoff instead of offering unrelated weekdays.
- Bound retention and document privacy because occupancy habits can be inferred
  from temperature-change history.

Acceptance: deterministic tests prove grouping, threshold/tolerance behaviour,
restart persistence, source attribution, dismissal suppression and that a saved
schedule changes only after explicit user confirmation. Accepted suggestions
must remain traceable and safely revertible unless a later schedule revision
creates a visible conflict.

Status: implemented for development validation in `0.14.7`. Production learning
is disabled by default. The remaining gates are full automated regression,
Home Assistant user testing and live evidence/notification review before a
learning release is declared stable.

## ZEAL Learning — Room Thermal Response

This work follows the source-aware audit and begins in observation-only mode.

Thermal observations and derived room models will use bounded, versioned Home
Assistant Store documents. ZEAL will not introduce MariaDB or a separate SQLite
database for this feature. The agreed volume, retention and compaction contract
is recorded in closed [#6](https://github.com/Buster1959/ZEAL/issues/6).
The agreed Learning page/module structure is recorded in closed
[#7](https://github.com/Buster1959/ZEAL/issues/7).

- Add an administrator Thermal Response Yes/No option. On first enable, ask one
  plain-language “How easily does your home stay warm?” question (five choices
  plus Not sure, with EPC bands only as an optional guide), a preferred local
  outdoor-temperature sensor, a fallback weather provider and included rooms.
  Do not ask for specialist building data. Explain that an inaccurate starting
  estimate only lengthens initial learning.
- Use the preferred local outdoor sensor for observations and the compatible
  weather entity for fallback current temperature and hourly forecast.
- For each next scheduled target, interpolate Home Assistant's timestamped
  hourly forecast across the candidate warm-up interval and solve backwards for
  the recommended start. Display current measured outside temperature separately
  from the forecast range/provider used by that prediction.
- Integrate against Home Assistant's weather contract rather than provider
  names; validate with Met Office, Open-Meteo and Pirate Weather-shaped entities.
- Store actual observations separately from forecasts and retain the provenance,
  quality and model version required to reproduce each estimate.
- Fit a per-room first-order thermal response: heat-up rate, response delay,
  cooldown/heat-loss behaviour and confidence as functions of the indoor/outdoor
  temperature difference and available heat-input signals.
- Refine included room models continuously without Accept/Edit/Dismiss proposals
  and provide administrator response graphs; keep automatic optimum start as a
  separate future opt-in.
- Reject or down-weight stale sensors, open-window periods, interrupted runs,
  manual changes, unexplained heat sources and likely solar/occupancy gains.
- Detect an abrupt unexplained per-room temperature rise, label it suspected
  external heat, pause only that room's model training, and resume after a
  defined period back inside its expected response envelope. Do not change
  demand, schedules or thermostat/TRV targets.
- Introduce advisory optimum start before any automatic behaviour. Show the
  current room/outside temperatures, next target/time, forecast range/provider,
  predicted warm-up and start, evidence and confidence.
- Keep automatic optimum start behind a later explicit opt-in and confidence
  threshold. Do not change the saved schedule period.
- Reserve PID for later proportional outputs; do not layer it over binary zone
  actuators or existing TRV/heat-source controllers.

Acceptance: synthetic models, provider-contract fixtures and restart/stale-data
tests prove parameter recovery, forecast/observation separation, per-room
isolation, explainable confidence and safe fallback to the unchanged schedule.

Status: planned for the next major version. The detailed specification and
sequencing are in `docs/LEARNING_ROADMAP.md`.
