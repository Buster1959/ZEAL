# ZEAL UI Acceptance Tests

Run these checks on desktop and in the Home Assistant Companion app. Use generic
dummy entities first. Record pass/fail, browser/app version and Home Assistant
version for each test.

## Navigation and access

- An administrator can open ZEAL from the sidebar and the integration's
  Configure action.
- A non-administrator cannot access configuration commands.
- Overview, Setup, Schedule and Quick Change navigation stays visible and the
  active page is clear.

## Setup

- Add, edit and remove a zone; select one actuator and heat source.
- Add Areas as rooms; verify an Area cannot be assigned twice.
- Physical thermostat and sensor choices are Area-scoped and contain no
  ZEAL-owned entities.
- Save, reload the page and confirm the hierarchy is unchanged.
- Open two pages, save one, and confirm the stale second page is rejected.

## Schedule

- Add, edit, drag and remove periods on every weekday.
- Confirm exact time/temperature fields and graphs agree after saving/reload.
- Confirm the previous target carries across midnight and empty days.
- Apply one source day to selected days.
- Copy a complete week to selected rooms without changing their Areas or
  equipment.

## Quick Change

- Apply relative and exact holds to a room, Zone/Floor, selection and whole
  house for each duration.
- Confirm saved schedules remain unchanged.
- Cancel one room and confirm it returns to the eligible scheduled target.

## Away and precedence

- Test Off, one dedicated calendar and one exact start/end period.
- Confirm only active rooms use the Away target.
- Confirm Quick Change is blocked while Away is active.
- Confirm an existing hold pauses and either resumes or expires correctly.
- Select **End Away now** and confirm normal control resumes immediately.
- Restart Home Assistant during Away and confirm correct reconciliation.

## Downloads and privacy

- Download configuration and audit JSON after known changes.
- Confirm saved hierarchy, schedules, Away settings, causes and outcomes agree
  with the UI.
- Confirm no credentials or tokens appear.
- Review names/entity IDs before sharing outside the installation.

## Responsive/mobile layout

- At narrow width, cards form one readable column without horizontal page
  scrolling.
- Buttons remain tappable and do not overlap labels or form fields.
- Schedule exact-entry fields remain usable without relying on graph dragging.
- Saving and error confirmations remain visible after the page scrolls.
