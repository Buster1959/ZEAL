# ZEAL V1 release-candidate review — resolution

This is the tracked resolution of the 44-finding review performed against
`7e37272` (`0.14.3`) on 1 September 2026. The resolution was completed on
`main` against manifest `0.14.7`.

Status has a strict meaning:

- **Fixed** — the defect or documentation mismatch was corrected and committed.
- **Open** — the finding is valid, but remains deliberate follow-up work.
- **False** — the claimed defect or collision is not present on the evidence
  available in this project.

Summary after independent code/documentation cross-check: **33 Fixed · 11 Open
· 0 False**. No finding is omitted. The cross-check initially found three
incorrect or incomplete Fixed claims plus two smaller follow-ups; each is
recorded below rather than overwriting the review history silently.

## Resolution ledger

| ID | Status | Resolution and evidence |
|---|---|---|
| A1 | **Fixed** | Cross-weekday keys no longer contain per-day `period_id`; a regression test uses distinct weekday IDs. `6687152` |
| A2 | **Fixed** | Evidence uses a room-schedule fingerprint; unrelated panel/configuration changes do not reset it, and both Accept and Revert use the current global optimistic token while exact-period matching guards the write. The fingerprint deliberately covers the whole seven-day room schedule, so a real edit to that room invalidates its other in-flight patterns. `6687152`, `0a61cd5` |
| A3 | **Fixed** | Away-period changes are retained as `excluded` with `away_mode_active`; detection now explicitly matches only `outcome=applied`. A mixed two-excluded/one-applied regression produces no proposal. `6687152`, correction `31c0a55` |
| A4 | **Fixed** | The per-room meaning of zone/whole-house Quick Change batches is now an explicit product decision; proposals remain per-room writes. `6eb0e39` |
| A5 | **Fixed** | Documentation now states the implemented count-based confidence and global control, and labels richer confidence/per-room controls as planned. `6eb0e39` |
| A6 | **Fixed** | Decision 16 now says the thresholds are named constants pending validated advanced controls. `6eb0e39` |
| A7 | **Fixed** | Proposal cards contain the agreed other-days banner and place **Open Schedule** inside it. `104a237` |
| A8 | **Fixed** | Events are pruned by both a 42-day age limit and the 5,000-event bound. Learning tests now use a clock-relative Monday, preventing the retention rule making CI fail as fixed 2026 fixtures age. `6687152`, correction `3d5e68e` |
| A9 | **Fixed** | Persistent-notification timing uses Home Assistant's clock. `6687152` |
| A10 | **Fixed** | The decision endpoint rejects proposal actions while Learning is disabled. `6687152` |
| B1 | **Fixed** | User and acceptance documents consistently treat **Overrides** as the page and Quick Change/Away as its features. `6eb0e39` |
| B2 | **Fixed** | README now describes the canonical ZEAL room target and labels highest-physical-TRV selection as startup fallback only; the code docstring matches. `6eb0e39` |
| B3 | **Fixed** | Architecture and data-model documents list all four versioned stores and the Learning runtime layer. `6eb0e39` |
| B4 | **Fixed** | Panel API documentation lists every input covered by the global optimistic revision and explains why it changes. `6eb0e39` |
| B5 | **Fixed** | Zone-control and both Learning WebSocket commands, including their permission rule, are documented. `6eb0e39` |
| B6 | **Fixed** | Hand-maintained exact test totals were removed; CI reports the current count. `091b074`, `6eb0e39`, `4a79496` |
| B7 | **Fixed** | The stale historical acceptance claim was removed, the current implementation baseline recorded, and Learning live gates added. Exact-candidate results correctly remain Pending until rerun. `4a79496` |
| B8 | **Fixed** | README now explains that translation equality is enforced by the automated suite. `6eb0e39` |
| B9 | **Fixed** | The i18n roadmap lists all current pages and the historical V1 review is explicitly labelled as predating Overrides/Learning. `6eb0e39` |
| B10 | **Open** | Learning now has a current-feature bullet and interface-tour section, but the required privacy-reviewed release screenshot has not yet been captured. `6eb0e39` |
| B11 | **False** | ZEAL Flow is an independent GitHub repository/project and is outside this repository's product plan. Active ZEAL planning no longer tracks its naming or design work. Superseded by the owner decision recorded after `ebb2129`. |
| C1 | **Fixed** | Overrides/Away behaviour is implemented directly in the panel; the string-replacing entry shim was deleted. `ec7e7c7` |
| C2 | **Fixed** | The panel loads one directly versioned asset and tests derive its URL from `PANEL_ASSET_VERSION`. `ec7e7c7` |
| C3 | **Fixed** | Only the readable Setup gate remains for the competing-scheduler warning. `ec7e7c7` |
| C4 | **Fixed** | Coordinator hierarchy access uses the declared constants. `2ec872c` |
| C5 | **Fixed** | Frozen Away configuration parses timestamps once and reuses the parsed values. `2ec872c` |
| C6 | **Open** | Per-view rendering or a Lit migration is valid larger work, intentionally deferred until Thermal Response needs independently updating room cards. |
| C7 | **Fixed** | The one-second control timer runs only on visible Overview and stops on other pages, hidden tabs and disconnect. `3289e64` |
| C8 | **Open** | Replacing `window.prompt` with a themed inline edit form remains valid UI work; backend validation still prevents an invalid schedule write. |
| C9 | **Fixed** | Narrow navigation uses an auto-fitting grid rather than four fixed columns. `120ae8e` |
| C10 | **Fixed** | Config entries no longer use the display name as a unique ID, so multiple default-named ZEAL instances are allowed. `796e024` |
| C11 | **Fixed** | Push, pull-request and manual CI now run pytest and compilation. `091b074` |
| C12 | **Fixed** | The Home Assistant test package is pinned and its corresponding HA version documented. `091b074` |
| C13 | **Open** | Correcting the persisted `name`/`friendly_name` semantics requires an explicit schedule-schema migration; it is not safe as a creation-only swap. |
| C14 | **Fixed** | New period names use the highest existing numeric suffix, preventing duplicates after deletion. `120ae8e` |
| C15 | **Fixed** | Decision 25 records why demand has no deadband and why the re-enable delay is the cycling control. `6eb0e39` |
| D1 | **Open** | Splitting Setup into Zones & rooms and Settings remains planned structural work before Thermal Response settings are added. |
| D2 | **Open** | Learning now has an active-status header and explicit Schedule suggestions section, but the Thermal Response sub-view awaits that feature's data model. `104a237` |
| D3 | **Open** | Weekdays, adaptations and statuses are now plain English and an evidence-range sentence is shown. A defensible estimated-effect calculation is not yet available and will not be invented. `104a237` |
| D4 | **Fixed** | Learning shows active-pattern counts, threshold progress and oldest-evidence expiry, limited to the backend-provided observation window. Threshold/window values now come from Python policy rather than duplicated JavaScript literals. `104a237`, `7ffcce0`, `8d2c78b` |
| D5 | **Open** | The Overview thermal-model slot depends on the Thermal Response model and remains a planned layout decision. |
| D6 | **Open** | A ghosted current/proposed timeline remains a useful enhancement; the exact textual diff is retained meanwhile. |
| E1 | **Open** | Cooling-direction and HVAC-mode seams are documented next-major work; V1 remains intentionally heating-only. ZEAL Flow is outside this repository's plan. |
| E2 | **Fixed** | The sibling-parity skill preserves separate authorization and now treats ZEAL Flow as an independent project rather than ZEAL backlog. `a53aa6d`, updated after `ebb2129` |

## Independent cross-check corrections

| Cross-check outcome | Resolution |
|---|---|
| Mixed Away and normal evidence could create a proposal | Confirmed. Backend matching now requires `outcome=applied`; regression covers `excluded`, `excluded`, `applied`. `31c0a55` |
| Fixed August 2026 evidence would age out and break tests | Confirmed. Learning fixtures are relative to the current Monday, preserving weekday intent indefinitely. `3d5e68e` |
| Revert retained the original global-revision coupling | Confirmed. Revert uses the current token and still verifies the exact accepted period; a sidebar-change regression is included. `0a61cd5` |
| JavaScript duplicated the 3-date/21-day policy | Confirmed. `get_learning` now supplies both values and the panel derives all progress calculations from them. `8d2c78b` |
| Learning payload schema remained implicit at version 1 | Confirmed. Payload schema 2 is separate from the HA Store envelope; legacy unmatchable evidence is ignored on load. `5055b20` |
| A2 room fingerprint covers all seven days | Confirmed and retained as a deliberate conservative boundary: a real edit anywhere in that room invalidates its other evidence. Period-level fingerprints may be considered later but are not represented as current behaviour. |

## Verification record

- Targeted regression coverage was added for cross-weekday evidence, room-scoped
  revisions, mixed Away exclusion, clock-relative age retention, revert after
  unrelated preference changes, disabled-Learning decisions,
  responsive navigation, period naming and timer lifecycle.
- Python compilation and change-integrity checks were run for each local update.
- The pinned CI workflow is the authoritative complete-suite result for every
  pushed `main` commit. Live Home Assistant observations deliberately remain
  **Pending** in `V1_ACCEPTANCE_RECORD.md`; this review does not convert automated
  evidence into a claimed real-home pass.

## Open-work boundary

The eleven Open items are not hidden V1 fixes. C6, D1, D2, D5 and E1 belong to the
Thermal Response/next-major architecture; C8, C13 and D6 require deliberate UI
or migration work; D3 needs a real effect model; B10 needs a privacy-reviewed
capture from Home Assistant; B11 needs a product naming decision. They should be closed by their own verified,
committed updates under the project workflow.
