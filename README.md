# TeamFlow · Phase 3

A real team and project management application built with Vue 3, Vite, PrimeVue Aura, Bootstrap grid/utilities, Lucide, Motion for Vue, Axios, Flask, Flask-SQLAlchemy, Flask-Login, and SQLite. Phase 1 authentication, teams, memberships, invitation codes, and settings remain available.

## Implemented

- Multiple teams and projects, with a per-user/per-team saved project selection. Every project and task request checks current membership on the server.
- Leader project creation/editing and task creation, assignment, reassignment, priority, deadline, status, and progress. Assigned members can update status/progress; other members can read and collaborate.
- A persisted Kanban board with optimistic drag/drop and rollback on rejected requests; My Tasks; combined search, status, priority, assignee, and deadline filters; deterministic deadline/priority/progress/update sorting.
- Wide task details with explicit Save, multiline comments, real supporting-file uploads/downloads, authorized attachment deletion, and task history.
- Backend-derived dashboard metrics, Chart.js status distribution, project/member progress, overdue tasks, rule-based workload, and a paginated activity feed.
- Ctrl/Cmd+K navigation, role-aware creation commands, team/project switching, and search of real loaded tasks and current teammates.
- Canonical light semantic colors, three surface levels, selective frosted overlays, pastel dashboard surfaces, subtle depth and motion, reduced-motion support, mobile navigation, and horizontal Kanban scrolling.
- Database-backed project folders/files, a light Monaco editor, explicit Save/Ctrl+S, session-scoped draft recovery, version conflicts, inherited permissions, task-file links, and saved-line code discussion with resolve/reopen.
- Authenticated Flask-SocketIO updates, project/file presence, lightweight cursor markers, persistent notifications, and workspace path search through the explorer and command palette.

Install both backend and frontend dependencies again for Phase 3. See [Phase 3 implementation and verification](docs/phase-three-verification.md) for models, routes, socket events, changed source tree, two-user instructions, results, and limitations.

## Run locally · Windows PowerShell

Use Python 3.10+ and Node.js 20.19+ or 22.12+. Open two terminals:

```powershell
cd C:\Users\ASUS\Desktop\TeamFlow\backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

```powershell
cd C:\Users\ASUS\Desktop\TeamFlow\frontend
npm.cmd install
npm.cmd run dev
```

Open http://localhost:5173. Existing installations can skip creating the environment and installing unchanged dependencies. This workspace's ignored environment files use backend **5001**, with a matching Vite API proxy, because another application occupied 5000. Fresh checkouts default to **5000**. Change `PORT` in `backend/.env` and `API_PROXY_TARGET` in `frontend/.env` together. The same-origin `/api` proxy carries session cookies; use `localhost` consistently for the frontend.

Optional `.env.example` files document `PORT`, `SECRET_KEY`, `FRONTEND_ORIGIN`, `COOKIE_SECURE`, `API_PROXY_TARGET`, and `VITE_API_BASE_URL`. Flask generates a persistent local session secret if one is not configured.

## Database and uploaded files

**No database reset is needed for the existing Phase 1 database.** Startup adds the five new tables through `create_all()` while preserving users, teams, and memberships. Existing tables are unchanged. SQLite lives in `backend/instance/teamflow.db`; uploads live in `backend/instance/uploads`. Back up both together. Instance data, secrets, virtual environments, node_modules, and build output are ignored.

New models: `Project`, `Task`, `Comment`, `Attachment`, and `Activity`. A team owns projects; projects own tasks; tasks own comment and attachment metadata. Relationships declare cascading behavior, but no project/task deletion control is exposed. Uploaded-file cleanup occurs through the attachment endpoint. Future changes to existing columns require a real migration; `create_all()` does not alter existing tables.

Uploads allow TXT, MD, CSV, JSON, PDF, PNG, JPG/JPEG, WebP, DOCX, XLSX, PPTX, and ZIP, with a nonempty-file limit of **10 MB** and a 12 MB request cap. Names are sanitized and storage uses random server-generated names. Files are served as downloads with `nosniff` after membership and task/file association checks. The uploader or a team leader may delete an attachment. These are supporting files, separate from Prompt 3 workspace files. Extension validation is not malware scanning.

## Progress, deadlines, workload, and versions

Project progress is the average progress of all its tasks, rounded to one decimal; an empty project is 0%. Member progress averages their assigned tasks. DONE always means 100%; setting progress to 100 completes the task. Reopening a completed task resets 100% to 0%; reducing completed progress without an explicit status reopens it as IN_PROGRESS. Forms explain the explicit Save behavior.

Deadlines are calendar dates, not UTC timestamps. The browser supplies its local `today` date to dashboard calculations; API callers that omit it use UTC's current date. Overdue means an unfinished task with a deadline earlier than today. Due soon means within the next three days; completed tasks have their own deadline state.

Workload sums active-task priority weights: LOW=1, MEDIUM=2, HIGH=3, URGENT=4, plus one point per task due within three days or already overdue. Scores 0–3 are Light, 4–7 Balanced, 8–11 High, and 12+ Overloaded. The dashboard explains this formula. This is rule-based analysis.

Task versions start at 1. Meaningful task updates and comment/upload/deletion mutations increment the version; no-op task saves do not. Client task saves submit the version they opened. Stale writes return 409, backed by SQLAlchemy's version check. Full conflict-review/merge UX remains reserved for Prompt 4.

## New API routes

| Method | Route | Access |
|---|---|---|
| GET / POST | `/api/teams/:team_id/projects` | Team member / leader |
| GET / PATCH | `/api/projects/:id` | Team member / leader |
| GET / POST | `/api/projects/:id/tasks` | Team member / leader |
| GET | `/api/projects/:id/dashboard?today=YYYY-MM-DD` | Team member; member analytics leader-only |
| GET | `/api/projects/:id/activity?offset=0` | Team member, pages of 50 |
| GET / PATCH | `/api/tasks/:id` | Team member / leader or assigned member |
| POST | `/api/tasks/:id/comments` | Team member |
| POST | `/api/tasks/:id/attachments` | Team member |
| GET / DELETE | `/api/tasks/:id/attachments/:attachment_id` | Team member / uploader or leader |

Phase 1 auth/team/user routes remain. Roles and actor IDs derive from the authenticated session. CSRF protects every mutation. Leaving/removal unassigns the departing member's tasks and records activity.

## Updated source tree

```text
TeamFlow/
├── backend/
│   ├── app/
│   │   ├── __init__.py, extensions.py
│   │   ├── models/       __init__.py, project.py
│   │   ├── routes/       auth.py, teams.py, users.py, projects.py, tasks.py
│   │   ├── services/     team_service.py, project_service.py
│   │   └── utils/        __init__.py
│   ├── tests/            test_phase_one.py, test_phase_two.py
│   ├── browser_review.py # Optional isolated browser QA server
│   ├── run.py, requirements.txt, .env.example
│   └── instance/         # Ignored database, session secret, uploads
├── frontend/
│   ├── src/
│   │   ├── assets/styles/ main.css, project.css
│   │   ├── components/
│   │   │   ├── common/    ActivityList.vue, CodeCard.vue
│   │   │   ├── navigation/ SideNav.vue, CommandPalette.vue
│   │   │   ├── project/   ProjectDialog.vue, ProjectEmpty.vue, ProjectState.vue
│   │   │   ├── tasks/     CreateTask.vue, TaskCard.vue, TaskDrawer.vue,
│   │   │   │              TaskFields.vue, TaskFilters.vue
│   │   │   └── team/      TeamForm.vue
│   │   ├── composables/   useTaskFilters.js
│   │   ├── layouts/       Shell.vue
│   │   ├── router/        index.js
│   │   ├── services/      api.js
│   │   ├── stores/        session.js, projects.js
│   │   ├── utils/         format.js
│   │   ├── views/         auth, onboarding, dashboard, tasks,
│   │   │                  team, activity, settings
│   │   └── App.vue, main.js
│   ├── tests/             task-filters.test.mjs
│   └── index.html, package.json, package-lock.json, vite.config.js, .env.example
├── docs/                 verification reports and browser screenshots
└── README.md, .gitignore
```

## Verification

```powershell
cd C:\Users\ASUS\Desktop\TeamFlow\backend
.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd C:\Users\ASUS\Desktop\TeamFlow\frontend
npm.cmd run build
npm.cmd test
```

Phase 2 result: **31 backend tests passed**, preserving all 13 Phase 1 tests, and **4 frontend tests passed** for filtering, deadline states, sorting, and reassignment. Backend tests isolate databases and upload storage. The frontend production build succeeds without build warnings after separating Vue and theme chunks. Added frontend dependencies: `chart.js` and `vuedraggable`; existing required libraries remain. Flask-Login emits one upstream `datetime.utcnow()` deprecation warning under the installed Python version.

See `docs/phase-two-verification.md` for the exact browser audit and limitations. `browser_review.py` optionally runs an isolated review database/upload directory on 5001; stop the normal backend before using it. Review accounts/data never seed the normal application.

## Reserved for later prompts

Prompt 3: workspace files/folders, Monaco, file permissions/linking, code comments, Socket.IO, live presence, cross-client updates, notifications, and collaborative editing foundations. Prompt 4: full conflict/merge UX, dependencies, blocked work, critical path, risk radar, advanced workload intelligence, and final audit. No inactive controls expose these features.

Other clients obtain changes on entry/manual refresh in this phase. Internet deployment still needs HTTPS, a production server, rate limits, and operational upload controls.
