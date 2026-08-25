# ZEAL V1 Block Plan

Each block is completed, tested, documented and committed before work begins on
the next block. V1 release work stays on `feature/v1-scheduler-html-ui` until
the complete branch is ready for review.

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

Acceptance: repository and Wiki agree, validation actions pass, and documentation
contains no personal installation details.

Status: in progress. HACS metadata, HACS/Hassfest workflows, ten setup-flow
language files, repository/Wiki user and technical guides, release draft,
privacy rules and UI acceptance tests are implemented. The complete automated
suite passes 122/122 and Hassfest passes. Actual ZEAL desktop/mobile screenshots
remain a Block 9 gate and must be captured from a generic test installation.
HACS currently rejects the existing PolyForm Shield licence because it cannot
identify it as a supported SPDX licence. The project owner has chosen to keep
PolyForm Shield through full testing and resolve the public-release licence
afterward; HACS validation is therefore an explicitly deferred release gate,
not an application-code failure.

## Block 10 — V1 validation and release preparation

- Run the full automated suite and live Home Assistant acceptance plan.
- Verify restarts, unavailable devices, multiple zones, multiple TRVs/sensors,
  persistence and 24-hour schedule/audit behaviour.
- Prepare the V1 manifest, release notes and reviewable merge to `main`.

Acceptance: all gates pass and no required V1 work remains.

Status: in progress. Automated tests, compilation, frontend syntax, JSON/YAML,
repository hygiene and release-metadata contracts pass. The live acceptance
matrix is recorded in `docs/V1_ACCEPTANCE_RECORD.md`. Manifest `1.0.0`, merge,
tag, GitHub release and HACS submission remain gated on the pending live checks,
screenshots and deferred licence decision.
