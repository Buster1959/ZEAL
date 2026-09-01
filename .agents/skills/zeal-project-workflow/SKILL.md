---
name: zeal-project-workflow
description: Apply ZEAL repository working conventions during code, documentation, testing, review, release, or maintenance changes in Buster1959/ZEAL.
---

# ZEAL Project Workflow

Use this skill for every change made in the ZEAL repository.

## Commit discipline

- Treat each coherent, verified update as its own checkpoint. Run the relevant
  checks, commit it, and push it to the current authorized branch before
  beginning the next independent update.
- Do not accumulate unrelated fixes, documentation edits, or review findings in
  the working tree for a later omnibus commit. For a large review, use one
  commit per finding or per inseparable group of findings that share one cause.
- If a check fails, keep working within that update until it passes or is
  explicitly classified as blocked; do not start another update meanwhile.
- Preserve the user's instruction that `main` remains current. Unless the user
  explicitly requests local-only work or another branch, push each completed
  commit to `origin/main`.
- After every commit, confirm the working-tree state before starting the next
  update. Never claim an update is committed or pushed without verifying it.

## Review traceability

When resolving a review, record each finding as **Fixed**, **Open**, or **False**
and cite the commit, verification, and concise rationale. **Open** means the
finding is valid but deliberately remains unresolved; **False** means the
reported behavior is not a defect or is not present in the reviewed revision.

## Sibling projects

For fixes with a concrete sibling-project connection, also use
`zeal-visual-scheduler-parity`. Authorization to change ZEAL does not authorize
changes in a sibling repository.
