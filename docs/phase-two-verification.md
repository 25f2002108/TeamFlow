# Phase 2 verification

Executed October 4, 2026, against the existing Phase 1 application.

## Automated checks

- Before implementation: original backend suite **13 passed**, and original frontend production build passed.
- Final backend command: `backend/.venv/Scripts/python.exe -m pytest -q` — **31 passed**, including all original tests. One upstream Flask-Login `datetime.utcnow()` deprecation warning remains.
- Final frontend command: `npm.cmd run build` — successful Vite production build, with no warnings after splitting Vue and theme bundles.
- Frontend `npm.cmd test` — **4 passed**, covering combined filters, calendar deadline states, deterministic sorting, and reactive reassignment/status updates.
- Installing Chart.js and vuedraggable completed successfully; npm reported zero vulnerabilities at installation.
- Backend coverage includes leader project creation/editing, project membership, task creation/assignment/reassignment, invalid fields/assignees, assigned-member work updates, unrelated-member denial, stale versions, no-op versions, DONE/reopen rules, multiline comments, activity records, attachment upload/download/delete authorization, path sanitization, size/type limits, dashboard progress/status/overdue/member/workload calculations, departing-member unassignment, and additive initialization preserving Phase 1 accounts/teams.

## Browser audit

The optional `backend/browser_review.py` ran against `backend/instance/phase-two-review.db` and `phase-two-review-uploads`. These are isolated QA accounts and actual records created through the interface. The normal development database was preserved.

| Journey / control | Observed result |
|---|---|
| Register, login, logout | Leader and member accounts registered; repeated login/logout succeeded |
| Create/join team | Leader created Northstar Studio; member joined using its lowercase invitation code |
| Team switching | A second team showed an empty project state; returning restored the prior team's selected project |
| Project creation | Real project appeared immediately; initial dashboard showed zero task counts and progress |
| Edit/switch projects | Second project created and renamed; selecting the first project survived page reload |
| Task creation | Real title, multiline description, member assignment, HIGH priority, and deadline saved |
| Drag/drop | Task physically dragged from To do to In progress; reload confirmed persisted status and version 2 |
| Leader progress save | 60% persisted; dashboard/member progress changed accordingly |
| Member permissions | Management inputs disabled; assigned member could save status/progress; setting 100% produced DONE |
| Reassignment/reopen | Leader reassigned work to themselves, reopened it in Review, saved 80%; board and workload reflected the change. Former assignee's My Tasks became empty and task work fields became read-only |
| Comments | Leader multiline comment and member comment persisted, updated counts and task history |
| Attachments | Leader and member each uploaded a real 49-byte TXT file; metadata, counts, authors, and versions updated. Member saw deletion only for their own file; confirmation opened and Cancel preserved it |
| Download | Button clicked without app console errors; browser automation's download event timed out. Exact downloaded bytes, response disposition, and access denials are verified by backend tests; a saved browser download was not confirmed |
| History/activity | Creation, assignment, status, progress, comment, upload, and reassignment records rendered from real data |
| Combined filters | Review plus LOW priority returned zero matches; Clear restored the task and filter defaults |
| Search/command palette | Ctrl+K opened it; searching Sam returned the real member; Enter opened Team with the member filter applied |
| Settings | Profile and team-name updates persisted and refreshed shell/context data |
| Mobile navigation | Navigation drawer opened; Activity destination displayed the database feed |
| Responsive inspection | Board inspected at 1440×1000, 1366×900, 768×1024, 390×844; horizontal board scrolling retained card widths. Dashboard checked desktop/tablet/mobile; mobile task drawer fitted the viewport |
| Console | No captured warning/error entries in the completed browser journeys |

The remaining filter/sort branches, role-aware commands, and delete confirmation wiring were inspected in source. Attachment deletion and member removal/leave permissions and persistence are covered by backend tests; they were not represented as additional Phase 2 browser deletions. Phase 1's earlier browser audit is retained in `verification.md`.

Screenshots: `phase-two-dashboard.png`, `phase-two-board.png`, `phase-two-mobile.png`. Screenshots depict isolated QA records, not seeded application content.

## Operational notes

The normal application is restored after the audit. Backend uses 5001 and Vite 5173 in this workspace. Another application on 5000 was left running. No database reset is required: new tables are added on startup. Cross-client synchronization, notifications, workspace/editor features, and full conflict UI remain deferred to Prompts 3–4.
