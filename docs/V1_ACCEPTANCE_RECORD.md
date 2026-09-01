# ZEAL V1 Acceptance Record

This is the release gate for ZEAL V1. A check is marked **Pass** only when it
has been observed against the release candidate named below. Automated tests do
not substitute for live Home Assistant, thermostat and actuator checks.

## Candidate

- Branch: `main`
- Current implementation baseline: `a53aa6d`
- Exact candidate commit tested: _pending after review closure_
- Manifest version to test: `0.14.7`
- Home Assistant version: _pending_
- Desktop browser/version: _pending_
- Companion app/platform/version: _pending_
- Live test start/end: _pending_

If any code changes after live testing begins, record the new commit and repeat
the checks affected by that change.

## Automated and repository gates

| Gate | Status | Evidence |
|---|---|---|
| Complete Python suite | Pending | CI must pass on the exact candidate; do not copy a historical test count |
| Python compilation | Pending | Run on the exact candidate |
| Frontend JavaScript syntax | Pending | Parse `zeal-panel.js` on the exact candidate |
| JSON and workflow YAML syntax | Pending | Parse all shipped metadata on the exact candidate |
| Tracked cache/placeholder scan | Pending | Repeat on the exact candidate |
| Manifest/HACS metadata contracts | Pending | Automated release-metadata tests on the exact candidate |
| Hassfest | Pending | GitHub validation on `main` at the exact candidate |
| HACS validation | Expected policy failure | PolyForm Shield is intentionally retained; custom-repository distribution does not require default-store licence eligibility |

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
| Learning capture | Three comparable manual changes on any three distinct dates within 21 days create one proposal, including independently created weekday period IDs | Pending |
| Learning day scope | Accept writes exactly the evidenced weekday/period; the banner directs broader changes to Schedule | Pending |
| Learning decisions | Edit-and-accept, snooze and dismiss persist across restart; accepted changes can be reverted | Pending |
| Learning exclusions | Away-period changes remain audited as excluded and never count toward a proposal | Pending |
| Desktop UI | Navigation, editing, confirmation and errors pass the UI acceptance plan | Pending |
| Mobile UI | Narrow layout, exact schedule entry and controls pass in Companion app | Pending |
| Privacy | Diagnostics, downloads and screenshots contain no credentials or personal installation details | Pending |

## Evidence to retain

- Configuration export taken at the beginning and end of the 24-hour run
- Audit export covering the same period
- Redacted diagnostics after the restart and unavailable-device checks
- Privacy-reviewed desktop screenshots in `docs/images`; add the corresponding
  mobile captures after Companion-app acceptance
- Notes for any discrepancy, even when the final result is correct

Do not commit real-home exports. Store them privately and add only the pass/fail
result and a non-identifying explanation to this record.

## Release sequence after every live gate passes

1. Add the remaining privacy-reviewed mobile screenshots and update the
   documentation links.
2. Change the manifest and release notes from pre-V1 to `1.0.0`.
3. Rerun the complete suite, compilation, frontend/metadata checks and Hassfest
   on the exact release commit; confirm HACS reports only the expected licence
   policy result.
4. Create the `1.0.0` tag and a full GitHub release from `main`.
5. Smoke-test one-click custom-HACS installation and updating from that release.

## Final sign-off

- All live gates passed: _pending_
- No unresolved V1 defects: _pending_
- PolyForm Shield licence and custom-HACS distribution confirmed: Yes
- Exact release commit: _pending_
- Approved for merge/tag/release: _pending_
