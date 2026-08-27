# ZEAL V1 Acceptance Record

This is the release gate for ZEAL V1. A check is marked **Pass** only when it
has been observed against the release candidate named below. Automated tests do
not substitute for live Home Assistant, thermostat and actuator checks.

## Candidate

- Branch: `main`
- Candidate commit tested: `5aacdc4` before the `0.13.1` distribution and
  instance-management fix; record the `0.13.1` commit when repeating UI checks
- Manifest version during testing: `0.13.1`
- Home Assistant version: _pending_
- Desktop browser/version: _pending_
- Companion app/platform/version: _pending_
- Live test start/end: _pending_

If any code changes after live testing begins, record the new commit and repeat
the checks affected by that change.

## Automated and repository gates

| Gate | Status | Evidence |
|---|---|---|
| Complete Python suite | Pass | 130/130 tests, 27 August 2026 |
| Python compilation | Pass | `custom_components` and `tests` |
| Frontend JavaScript syntax | Pass | `zeal-panel.js` parsed by Node.js |
| JSON and workflow YAML syntax | Pass | All shipped metadata parsed |
| Tracked cache/placeholder scan | Pass | No shipped cache or release placeholders |
| Manifest/HACS metadata contracts | Pass | Automated release-metadata tests |
| Hassfest | Pass | GitHub validation on the V1 feature branch |
| HACS validation | Deferred | Only PolyForm Shield identification fails; licence decision follows full testing |

## Live Home Assistant gates

| Area | Required observation | Status |
|---|---|---|
| Clean installation | Install the candidate on a clean test system, restart and add ZEAL | Pending |
| Existing configuration | Load/modify a pre-panel configuration without losing assignments | Pending |
| Overview and Setup | Add/edit/remove zones and rooms; Area-scoped equipment is correct | Pending |
| Entity separation | ZEAL thermostats never appear as physical TRV/sensor choices | Pending |
| Multiple equipment | At least one room with multiple TRVs and multiple sensors behaves correctly | Pending |
| Multiple zones | Independent zones drive only their own actuator and rooms | Pending |
| Demand safety | Demand, all-valves-closed protection, re-enable delay and Manual override work | Pending |
| Weekly schedule | All displayed transitions, including midnight carry, execute correctly | Pending |
| 24-hour comparison | Configuration and audit exports agree with a complete day of intended targets | Pending |
| Quick Change | Room/zone/selection/whole-house holds apply, expire/cancel and never edit the week | Pending |
| Away date range | Start, end, early cancellation and restart reconciliation work | Pending |
| Away calendar | Calendar activation/end, unavailable state and early cancellation work | Pending |
| Precedence | Away, holds, manual room target, schedule and zone Manual override follow the documented order | Pending |
| Device failure | Unavailable and stale TRVs/sensors notify, degrade safely and recover | Pending |
| Persistence | Setup, schedules, Away and audit survive Home Assistant/integration restarts | Pending |
| Desktop UI | Navigation, editing, confirmation and errors pass the UI acceptance plan | Pending |
| Mobile UI | Narrow layout, exact schedule entry and controls pass in Companion app | Pending |
| Privacy | Diagnostics, downloads and screenshots contain no credentials or personal installation details | Pending |

## Evidence to retain

- Configuration export taken at the beginning and end of the 24-hour run
- Audit export covering the same period
- Redacted diagnostics after the restart and unavailable-device checks
- Generic desktop and mobile screenshots listed in `docs/images/README.md`
- Notes for any discrepancy, even when the final result is correct

Do not commit real-home exports. Store them privately and add only the pass/fail
result and a non-identifying explanation to this record.

## Release sequence after every live gate passes

1. Resolve the release licence and make HACS validation pass.
2. Add privacy-reviewed ZEAL screenshots and update the documentation links.
3. Change the manifest and release notes from pre-V1 to `1.0.0`.
4. Rerun the complete suite, compilation, frontend/metadata checks, Hassfest and
   HACS validation on the exact release commit.
5. Open the reviewable merge from the V1 feature branch to `main`.
6. After merge, create the `1.0.0` tag and a full GitHub release from `main`.
7. Smoke-test installation from that release before requesting default HACS
   inclusion.

## Final sign-off

- All live gates passed: _pending_
- No unresolved V1 defects: _pending_
- Release licence resolved: _pending_
- Exact release commit: _pending_
- Approved for merge/tag/release: _pending_
