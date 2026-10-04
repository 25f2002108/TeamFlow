# TeamFlow Prompt 3 implementation and verification

## Delivered

One canonical light theme now covers authentication, navigation, dashboard, Kanban, task drawers, workspace, forms and overlays. Semantic tokens define cool off-white surfaces, violet accents, restrained shadows, frosted panels and readable text. There is no dark-mode switch.

Workspace stores project folders and files in SQLite, with hierarchy, path search, context actions, create, rename and confirmed deletion. Monaco provides light syntax highlighting for Python, JavaScript, TypeScript, HTML/Vue, CSS, JSON, Markdown and YAML; unknown extensions use plain text. Three resizable desktop panels become editor-first tablet/mobile layouts with explorer/context drawers. Save is explicit through the button or Ctrl/Cmd+S. File-name validation prevents traversal and ambiguous sibling names; file content is limited to 512 KiB.

Drafts are keyed by user/project/file in sessionStorage. Switching, leaving or signing out prompts when dirty. A newer remote version never overwrites a dirty draft; stale saves return 409 with current server content. Download draft and explicitly discard/reload are available. Drafts are local to the browser session, not a durable cross-device backup.

Permissions are server-enforced: VIEW reads/discusses; EDIT also saves content; FULL_ACCESS also creates within folders, renames and deletes; NO_ACCESS denies access. Default is VIEW. The nearest explicit ancestor rule applies, except any NO_ACCESS ancestor blocks its subtree. Leaders always have FULL_ACCESS and alone manage member rules and task-file links. Recursive deletion requires authority over every descendant. Permissions and membership are checked again on HTTP requests and socket context changes.

Related Files in task details links real project files and navigates to Workspace with file/task context. Code comments anchor to saved line ranges and versions; markers appear in Monaco's gutter. Discussion is flat, with resolve/reopen and optional linked-task context.

Flask-SocketIO runs inside the same Flask service. Cookie sessions plus a CSRF handshake authenticate connections. Authorized team/project/file contexts drive live project refreshes, notifications and sanitized presence. Team membership and file access changes revoke contexts. Presence distinguishes viewing/editing and carries lightweight cursor positions; it is not shared character-by-character editing. Reconnect rejoins the current context and reloads persisted data. Notification records support individual/all read actions and entity navigation.

## New models

`WorkspaceNode`, `FilePermission`, `TaskFile`, `CodeComment`, `Notification` in `backend/app/models/workspace.py`. Existing project/task/activity records are reused. Startup adds five new tables with `create_all()`; **no reset or existing-table migration is required**. Back up `backend/instance/teamflow.db` and uploads before upgrades. Future existing-column changes require migrations.

## API and events

All paths below have `/api` prefix and retain session/CSRF/membership checks.

| Routes | Purpose |
| --- | --- |
| GET/POST `/projects/:id/workspace` | Accessible tree; create node |
| GET/PATCH/DELETE `/workspace/nodes/:id` | Read; versioned save/rename; authorized deletion |
| GET/PUT `/workspace/nodes/:id/permissions` | Leader member rules |
| GET/POST `/tasks/:id/files`, DELETE `/tasks/:id/files/:nodeId` | Task-file relationships |
| POST `/workspace/nodes/:id/comments`, PATCH `/workspace/comments/:id` | Anchored comments; resolve/reopen |
| GET `/notifications`, PATCH `/notifications/:id/read`, POST `/notifications/read-all` | Persistent notification state |

Client events: `join_context`, `editing`. Server events: `project_changed`, `team_changed`, `presence_snapshot`, `notifications_changed`, `access_changed`. Mutation payloads trigger authorized HTTP refreshes rather than trusting client-provided content. The Vite proxy forwards `/api` and `/socket.io` to the same backend.

## Important changed tree

```text
backend/
  app/models/workspace.py
  app/services/workspace_service.py
  app/routes/workspace.py
  app/routes/notifications.py
  app/realtime.py
  app/__init__.py, extensions.py
  tests/test_phase_three.py
  run.py, browser_review.py, requirements.txt
frontend/
  src/assets/styles/{main,project,workspace}.css
  src/views/workspace/Workspace.vue
  src/components/workspace/
    MonacoPane.vue, FileTree.vue, ExplorerPane.vue
    ContextPane.vue, PermissionsDialog.vue
  src/components/tasks/{RelatedFiles,TaskDrawer}.vue
  src/components/navigation/{CollaborationControls,CommandPalette,SideNav}.vue
  src/stores/{workspace,collaboration}.js
  src/layouts/Shell.vue
  src/router/index.js, src/main.js, src/utils/format.js
  vite.config.js, package.json, package-lock.json
docs/screenshots/phase-three/
```

## Dependencies and exact run commands

Added Flask-SocketIO and simple-websocket to Python requirements; Monaco Editor and socket.io-client to npm. DOMPurify is overridden to 3.4.16; dependency installation reported zero vulnerabilities.

Backend, PowerShell:

```powershell
cd C:\Users\ASUS\Desktop\TeamFlow\backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

Frontend, second terminal:

```powershell
cd C:\Users\ASUS\Desktop\TeamFlow\frontend
npm.cmd install
npm.cmd run dev
```

This workspace uses backend port 5001 and frontend http://localhost:5173. Environment examples default to backend 5000; PORT and API_PROXY_TARGET must agree. `/socket.io` is proxied with WebSocket support. The local threaded Werkzeug service is for development; production deployment is outside this prompt.

## Two-user check

1. Sign in as leader in one browser and as a teammate in another browser/private session. Join the same team and choose the same project.
2. Leader creates a folder/file, links it through a task's Related Files, and grants teammate EDIT. Both open that file. Verify both appear in live collaborators.
3. Member saves code; leader's clean editor updates. Keep a leader draft while member saves again: verify conflict/draft protection. Member adds a saved-line comment; leader sees it and resolves it.
4. Assign a task to the member; check their notification badge, notification navigation, and mark read. Update task progress and compare board/dashboard without manual refresh.
5. Change access to VIEW and NO_ACCESS, then restore. Verify save controls/room context respond and inaccessible files disappear. Disconnect/reconnect one browser and verify presence and fresh data.

## Verification actually performed

- Backend: 47 tests passed. Existing 31 phase-one/two tests remain green; 16 phase-three cases cover hierarchy/cascade, name validation, inherited permissions and denial, full-access limits, stale versions, cross-project linking, comments/resolve, notifications ownership/read, private activity, authenticated two-client sockets, task/dashboard changes, cursor/editing presence, live comments/file saves, reconnection, room denial and membership revocation.
- Frontend: all four existing filter/deadline/sort tests passed.
- Production Vite build passed. Monaco is route-lazy; its approximately 3.24 MB minified Workspace chunk and JSON feature chunk still trigger Vite's size warning.
- Actual browser: 1440 desktop, 1280 laptop, 768 tablet and 390 mobile. Created `review.py` in the isolated review database, typed Python through Monaco, saved via Ctrl+S, posted a saved-version line comment, changed a real member's rule to EDIT, linked the file through the task drawer and navigated back with task context. Then signed in as member, confirmed EDIT and hidden creation/permission controls, saved content to version 3, opened a real permission notification and marked all read to zero. Tablet editor priority and mobile explorer/task-context drawers were inspected. Screenshots are in `docs/screenshots/phase-three`.
- Two simultaneously authenticated users were tested through Flask-SocketIO test clients. Two simultaneous browser sessions were **not** manually audited. UI deletion and every permission-state transition were not manually exercised; automated backend tests cover those cases. No exhaustive accessibility audit was performed.

## Prompt 4 and limitations

Full merge/conflict resolution, task dependencies, blocked/critical-path/risk logic, final demo polish and final comprehensive audit remain for Prompt 4. File discussion uses saved line/version anchors; anchors do not automatically remap after edits. Presence is process-local, so multi-worker production deployment needs a shared Socket.IO message queue. Realtime uses authorized refresh events, not CRDT/OT collaboration. Monaco bundle weight is the principal build warning. Flask-Login emits one upstream `datetime.utcnow()` deprecation warning in the remember-me test.
