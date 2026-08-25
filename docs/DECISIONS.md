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
