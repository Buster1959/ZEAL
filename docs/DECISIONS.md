# ZEAL V1 Decision Summary

This page records the decisions that define the current V1 implementation. The
companion Wiki retains the longer chronological design history.

1. ZEAL and Visual Climate Scheduler are independent integrations with no
   runtime dependency in either direction.
2. Do not let ZEAL and another thermostat setpoint scheduler control the same
   thermostat entities.
3. A ZEAL zone owns exactly one heating actuator and may contain several Home
   Assistant Areas as rooms.
4. Every room schedule targets one ZEAL-owned canonical thermostat; physical
   room TRVs are downstream equipment, never independent schedule targets.
5. A room uses the average of its usable temperature sensors and the highest
   usable physical-TRV target when the canonical target is unavailable.
6. All physical setpoint writes are clamped to 5–30°C.
7. Each heat source suggests a starting re-enable delay, but the saved delay is
   user-editable.
8. Weekly schedules are seven independent daily timelines with cross-midnight
   carry. Copying replaces schedules only.
9. Quick Change is temporary runtime state and never edits the saved week.
10. Away activation is Off, one Home Assistant calendar or one exact date
    range. The sources are mutually exclusive and Away can be ended early.
11. Room target precedence is Away, Quick Change, manual room target until the
    next transition, then weekly schedule. Zone Manual override remains the
    highest actuator authority.
12. Configuration changes use validated admin-only WebSocket commands and an
    optimistic revision token to reject stale browser writes.
13. Audit retention is bounded at 500 outcomes and excludes credentials.
14. V1 is heating-only. Cooling fields are reserved with safe defaults but are
    not exposed or acted upon.

## Next-major-version design constraints

15. Learning uses source-aware, persistent setpoint history and explainable
    evidence; it must not infer patterns solely from the current thermostat
    value.
16. Repetition thresholds, comparable time windows and observation periods are
    named constants with one definition. Advanced settings may expose them only
    after production evidence justifies safe tuning controls.
17. A learned pattern creates a proposal, not a schedule mutation. The saved
    week changes only after explicit user acceptance or editing through the
    normal revision-checked schedule API.
18. Accepted, edited, dismissed and snoozed proposals are audited. Retention is
    bounded and treated as occupancy-sensitive data.
19. The two named learning workstreams are **ZEAL Learning — Schedule
    Adaptation** and **ZEAL Learning — Room Thermal Response**.
20. Thermal Response selects standard Home Assistant outdoor-temperature and
    weather entities by capability; Met Office, Open-Meteo and Pirate Weather
    form the initial compatibility matrix, not an allow-list.
21. Actual outdoor observations train the room model; forecasts are used only
    for future optimum-start prediction and remain distinguishable in storage.
22. Thermal models are per room and begin with an explainable first-order model.
    PID is deferred unless ZEAL later controls a suitable proportional output.
23. Optimum start begins as a recommendation. Any automatic start adjustment
    requires explicit opt-in, sufficient confidence and safe fallback to the
    unchanged weekly schedule.
24. Schedule Adaptation is implemented and tested as one complete
    capture–classify–detect–recommend–confirm–commit–revert pipeline rather than
    shipping an observation-only phase first. Synthetic dated event streams
    exercise the production classifier and proposal engine because a stable
    household may generate too few natural changes for timely passive
    validation. Automatic detection may create advice, but only an explicit,
    authorised, revision-checked confirmation may change the saved schedule.
25. Schedule Adaptation has an administrator Yes/No control in Setup. Setup is
    the administrator's routine evidence-progress surface. **Schedule Updates**
    appears to administrators and Schedule/Learning-authorised standard users
    only when an actionable recommendation exists, and hides from standard
    users after all recommendations are resolved. Diagnostics remain a
    pseudonymised support mechanism, not the normal progress UI.
26. Heating demand has no temperature deadband: any positive difference between
    target and measured room temperature is demand. The per-zone re-enable delay
    bounds actuator cycling; adding a second hysteresis mechanism would obscure
    that control and previously proved ineffective in the source controller.
27. Thermal Response has an administrator Yes/No control in Setup. Enabling it
    asks one simple EPC question, selects a preferred local outdoor-temperature
    sensor and fallback weather provider, and confirms the participating rooms.
    The EPC answer is only a starting estimate: continuous per-room observations
    refine the model without proposal acceptance, while automatic optimum start
    remains a separate future opt-in.
