---
name: zeal-visual-scheduler-parity
description: Check whether a fix found in ZEAL also applies to HA Visual Climate Scheduler, ZEAL Flow, or another ZEAL-family sibling, and request approval before applying the related patch there. Use during debugging, implementation, or review when underlying behavior may be shared.
---

# ZEAL Sibling-Project Patch Parity

ZEAL and HA Visual Climate Scheduler have sibling code and documentation. The
name **ZEAL Flow** is currently ambiguous: it names the public mechanical
retrofit repository and also the planned private heating-and-cooling V2
repository. Do not use this skill to resolve or redefine that naming decision.
When a task says ZEAL Flow and its target is not otherwise clear, establish
which repository the user means before inspecting or proposing a sibling patch.

When a discovered fix has a concrete connection to the sibling project:

1. Inspect the sibling project read-only far enough to establish whether the
   same behavior or code path exists. Do not perform a speculative full audit
   after every unrelated change.
2. Complete the work already authorized in the current project.
3. Tell the user why the fix appears relevant to the sibling project, what
   behavior or files would be affected, and any adaptation the sibling needs.
4. Ask whether the corresponding patch should be applied to the sibling
   project.
5. Do not edit, commit, push, deploy, or release the sibling patch until the
   user confirms. Authorization for one project does not extend to the other.

If the user already requested the same fix in both projects, apply it to both
without asking again. If the read-only check finds no meaningful connection,
continue without interrupting the user.
