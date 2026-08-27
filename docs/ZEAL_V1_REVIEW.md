# ZEAL V1 Repository Review

> Historical Block 0 baseline. Later blocks have resolved several gaps recorded
> here; use [PROJECT_PLAN.md](PROJECT_PLAN.md) and
> [PROJECT_MANIFEST.md](PROJECT_MANIFEST.md) for current status.

Review date: 24 August 2026

Source branch: `main` at `505a9ca`
Historical implementation branch: `feature/v1-scheduler-html-ui` (later
fast-forwarded to `main`; see `PROJECT_MANIFEST.md` for current status)

## Executive finding

ZEAL has a substantial pre-V1 heating-control backend, but it is not yet a
coherent V1 product. The Coordinator, room thermostat, zone override, demand
sensor, device-health handling and native configuration flow exist. The
scheduler, professional HTML configuration panel, HACS packaging, consistent
versioning, consolidated tests and release-grade user documentation do not.

Visual Climate Scheduler and ZEAL will remain separate integrations. ZEAL will
contain an adapted, ZEAL-owned scheduler implementation; it will not import or
require `visual_climate_scheduler` at runtime.

## Current implementation

- Domain and package: `zeal` / `custom_components/zeal`
- Config-entry and Options Flow for zones, Areas, switches, heat source,
  re-enable delay, TRVs, sensors and room activation
- One ZEAL room thermostat climate entity per configured room
- Coordinator demand calculation and zone-switch control
- Per-zone manual override switch and demand sensor
- Multi-TRV propagation, multi-sensor averaging and setpoint safety bounds
- Re-enable-delay persistence, all-TRVs-off pump protection, state listeners,
  unavailable/stale entity handling and persistent notifications
- Diagnostics export and bundled brand icon
- Wiki containing architecture history, decisions and future design

## Material gaps and inconsistencies

### Product functionality

- At review, no time-based scheduler was implemented. Block 2 has since added
  the ZEAL-owned pure schedule model, engine and storage boundary. Block 3 has
  since added canonical-room execution, and Block 6 has added the seven-day
  visual editor.
- Block 8 has since added persisted calendar-driven or exact-date-range Away
  mode, active-room scoping, restart reconciliation and explicit precedence.
- At review, setup used the native Options Flow. Blocks 4 and 5 have since added
  the secure panel API and HTML Overview/Setup experience, and retired the
  multi-page Options Flow.
- Configuration export, bounded schedule-application audit storage, Quick
  Change and both panel downloads are complete through Block 7.
- No migration/import path exists for a Visual Climate Scheduler export.

### Versions and releases

- At review, Git history labelled the current work `0.13.0` while
  `manifest.json` reported `0.10.0`. Block 1 aligned the manifest to `0.13.0`.
- The only GitHub release is the old `0.1.0` prerelease.
- README statements conflict: the introduction says the Coordinator has not
  been validated, while later roadmap text says it was tested in a real dev
  environment.

### Tests

- At review, the declared test dependency was not installed in the workspace.
  Block 1 established an isolated test environment and verified 38/38 cases.
- At review, the newer Coordinator suite was misplaced inside production code.
  Block 1 moved its complete byte-verified contents to
  `tests/test_coordinator_full.py` and removed both obsolete copies.
- The consolidated suite exposed dormant safety specifications that the current
  Coordinator did not yet satisfy. Block 1 implemented setpoint clamping,
  stale-reading rejection and debounced offline/recovery notifications before
  accepting the baseline.
- Block 2 added 25 pure tests for schedule persistence/migration, selection,
  editing, room reconciliation and overrides. Blocks 3–6 added runtime,
  configuration/audit API, catalog separation and HTML panel contracts.
  Block 7 added restart-persistence and Quick Change/download contracts.
  Block 8 added Away validation, runtime transitions, precedence, API and panel
  contracts, bringing the complete suite to 118 cases.

### HACS and repository packaging

- No root `hacs.json` exists.
- No HACS or Hassfest GitHub Actions exist.
- There is no release manifest, structured release-note history or V1
  acceptance checklist comparable to Visual Climate Scheduler.

### Documentation

- The README is comprehensive but mixes current behaviour, incident history,
  test instructions, design decisions and future work.
- The Wiki is strong as a design record but lacks a concise installation and
  user guide, scheduler guide, HTML setup guide, screenshot set and release
  notes.
- Repository and Wiki naming/structure do not yet match the established Visual
  Climate Scheduler documentation pattern.

## V1 target architecture

```text
ZEAL config entry
  +-- ZEAL configuration (zones, rooms, devices, heat-source policy)
  +-- ZEAL Coordinator (demand, safety, pumps/relays, health)
  +-- ZEAL room thermostat entities (canonical setpoint boundary)
  +-- ZEAL-owned schedule model and Store
  +-- ZEAL schedule runtime and application audit
  +-- Admin-only ZEAL HTML panel and WebSocket API
        +-- Overview
        +-- Setup
        +-- Schedule
        +-- Quick Change
        +-- Downloads
```

The scheduler will identify rooms by ZEAL's stable room IDs and apply targets
only through the canonical ZEAL room thermostat boundary. It will never treat
the underlying physical TRVs as independent schedule targets.

## Independence and competing-scheduler rule

ZEAL and Visual Climate Scheduler remain independently installable, versioned
and released. They will not import, configure, detect, disable or require one
another.

The user-facing safety rule is generic:

> Do not assign a thermostat to more than one thermostat setpoint scheduler.
> If ZEAL and another integration, automation, blueprint or schedule both
> change the same thermostat's target temperature, they may repeatedly
> overwrite each other. Before enabling ZEAL scheduling, disable any other
> setpoint scheduler controlling those thermostat entities.

## Transplant boundary

Adapt from Visual Climate Scheduler V1.0.1:

- Schedule model, validation, migration and deterministic engine
- Day and room-copy editing semantics
- Temporary override calculations
- Versioned schedule Store and bounded application audit
- Admin-only WebSocket and panel-registration patterns
- Seven-day visual editor, Quick Change and JSON downloads
- Pure unit tests and human-facing UI acceptance tests

Do not transplant unchanged:

- The `visual_climate_scheduler` domain or storage keys
- Generic room/zone creation and arbitrary climate-entity assignment
- Standalone integration lifecycle or single-entry assumptions
- Visual Climate Scheduler branding, documentation or release identity

## V1 completion sequence

1. Consolidate and run the existing ZEAL tests; establish truthful versioning.
2. Add a ZEAL-owned schedule model and transplant pure scheduler tests.
3. Add a typed adapter between ZEAL rooms and their canonical room thermostats.
4. Add schedule runtime, restart reconciliation, timers, temporary holds and
   audit storage.
5. Add a single admin-only ZEAL panel for overview, setup, scheduling, Quick
   Change and downloads; retain only the minimal initial Config Flow.
6. ~~Add calendar/date-range Away mode and its safety/precedence tests.~~ Done
   in Block 8.
7. Standardize repository docs, Wiki, screenshots, manifests, actions and V1
   release materials.
8. Run automated and live Home Assistant acceptance tests before V1 release.
