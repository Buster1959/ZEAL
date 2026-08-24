# ZEAL V1 Repository Review

Review date: 24 August 2026  
Source branch: `main` at `505a9ca`  
Implementation branch: `feature/v1-scheduler-html-ui`

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

- No time-based scheduler is implemented.
- No calendar-driven away mode is implemented.
- No HTML configuration or overview panel exists; setup is a long native
  Options Flow.
- No built-in configuration download or schedule-application audit exists.
- No migration/import path exists for a Visual Climate Scheduler export.

### Versions and releases

- Git history labels the current work `0.13.0`, while `manifest.json` reports
  `0.10.0`.
- The only GitHub release is the old `0.1.0` prerelease.
- README statements conflict: the introduction says the Coordinator has not
  been validated, while later roadmap text says it was tested in a real dev
  environment.

### Tests

- The declared test dependency is not installed in the current workspace, so
  the baseline suite cannot presently be executed here.
- `tests/test_coordinator.py` contains the normal discoverable suite, while a
  newer, larger `custom_components/zeal/test_coordinator.py` is misplaced
  inside production code and is not part of the documented `pytest tests/`
  command.
- Scheduling, panel API, persistence migration, config editing and frontend
  workflows have no tests because those components do not yet exist.

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
6. Add calendar-driven away mode and its safety/precedence tests.
7. Standardize repository docs, Wiki, screenshots, manifests, actions and V1
   release materials.
8. Run automated and live Home Assistant acceptance tests before V1 release.
