# Phase 1 verification

Executed on October 4, 2026.

- Backend: `backend/.venv/Scripts/python -m pytest -q` — **13 passed**. Flask-Login emits one upstream Python 3.13 `utcnow()` deprecation warning on remember-cookie creation.
- Frontend: `npm.cmd run build` — successful production build with lazy route chunks; no size warning after splitting routes.
- Dependency install: npm reported **0 vulnerabilities**.
- Browser review: 1366×900 desktop, 768×1024 tablet, and 390×844 mobile.
- Browser console: no warning/error entries captured in the completed successful journeys. Invalid team code deliberately tested and returned useful feedback.

## Browser interaction audit

| Control / flow | Observed result |
| --- | --- |
| Register / sign in / sign out | Real sessions created, login accepted, logout returned to login |
| Account reload | Session restored without exposing unauthenticated protected content |
| Create team | Team created, invitation code displayed, leader role assigned |
| Join team | Lowercase code accepted, real member added to existing team |
| Invalid code | Useful inline error, submission available for retry |
| Team switcher | Second team created; switching loaded the correct team |
| Copy team code | Clipboard API resolved and success toast / copied label appeared |
| Profile and team-name forms | Saved values confirmed after full page reload |
| Member visibility | Both real test users visible; code / removal / rename absent for MEMBER |
| Search members | Filtered list, empty state, and Clear search worked |
| Refresh members | Real database membership loaded |
| Remove member | Confirmation displayed on mobile; accepted removal persisted after reload |
| Leave team | Cancel preserved membership; acceptance navigated to onboarding; rejoining worked |
| Navigation / account menus | Implemented destinations opened and mobile drawer dismissed after navigation |
| Empty team | Single-leader invitation state displayed |
| Backend unavailable | Initial connection error with Retry rendered during connection diagnosis |
| Responsive layout | Sidebar on desktop; drawer and adapted list on mobile; stacked sections on tablet |

The saved desktop screenshot uses disposable browser-verification accounts. Those accounts are not application seed data. The verification database is archived in the ignored backend instance directory, leaving the development database empty for your first registration.

The local backend uses port 5001 because another app already held 5000. Ignored local environment files configure the backend and Vite proxy consistently. No unrelated process was stopped.
