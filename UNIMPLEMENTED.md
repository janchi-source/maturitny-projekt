# ProMat – Unimplemented / Incomplete Features

Features that exist in the UI or are listed as DONE in the README but are **not fully working end-to-end**.

---

## 🔴 Not Functional At All

### Dark / Light Theme Toggle
- `main.js` has `initDarkMode()` wired to `[data-theme-toggle]` click events
- **No element with `data-theme-toggle` exists in any template**
- The dark class is hardcoded in `base.html`: `<html class="dark">`
- Users cannot switch themes at all
- **Fix needed:** Add a toggle button (e.g. in `header.html`) with `data-theme-toggle`

---

### AI Chat / Summarize / Search
- All three `AIService` methods in `app/services/ai_service.py` return placeholder strings:
  - `chat()` → `"[AI response placeholder – implement with Ollama]"`
  - `summarize()` → `"[AI summary placeholder – implement with Ollama]"`
  - `search_terms()` → `["[AI search placeholder – implement with Ollama]"]`
- The routes, UI, and fetch calls are all wired correctly — only the AI logic itself is missing
- Marked as owner's responsibility in the README

---

### Dashboard AI Insights
- The three AI insight cards on the dashboard are **hardcoded static data** in `app/blueprints/dashboard.py` (lines 29–53)
- They show fake project names, fake timestamps, and fake descriptions on every page load
- No actual AI analysis is happening; the data never changes

---

### Header Search Bar
- A search `<input>` is rendered in `header.html` on every page with placeholder _"Search projects, AI insights, or docs..."_
- **No JavaScript handler** attached to it
- **No backend route** processes the query
- Typing and pressing Enter does nothing

---

### Email Notifications
- `_notify_user()` in `app/blueprints/tasks.py` creates two `Notification` DB records per event — one with `channel="in_app"`, one with `channel="email"`
- **No SMTP configuration exists anywhere in the codebase**
- **No actual email is ever sent** — the `channel="email"` record is just a flag in the database
- The in-app notification center works; email delivery does not

---


## ✅ Actually Working (Clarifications)

These were uncertain but confirmed working end-to-end:

| Feature | Notes |
|---------|-------|
| Kanban drag-and-drop | HTML5 Drag API + `POST /tasks/<id>/quick-update` |
| Reports (burndown, throughput, cycle time) | Real DB queries, live data |
| Notification center page `/tasks/notifications` | Real data, mark-as-read works |
| API tokens & webhook endpoint | Token auth, `task.create` / `task.update_status` events |
| CSV import / export | Full parse + insert on import |
| Automation rules | Trigger/action execution on task update |
| Settings page (`/settings/`) | Profile update + password change |
| Task detail (checklists, comments, attachments, activity) | Fully functional |
| Granular project permissions (viewer/member/manager/admin) | Enforced on write routes |

---

## Phase 12 — Not Started

The following milestone streams are listed as `⬜ TODO` in the README and have **no implementation at all**:

| # | Stream |
|---|--------|
| 12.1 | Task Core vertical slice (end-to-end delivery focus) |
| 12.2 | Collaboration: mentions, attachments, timeline, watchers |
| 12.3 | Planning: dependency graph, advanced board controls |
| 12.4 | Governance: granular permissions admin tooling |
| 12.5 | Scale & Insights: saved filters, bulk actions, reporting, automation |

> Note: Many of the individual items under Phase 12 (11.1–11.18) were implemented separately — Phase 12 represents intentional "delivery slice" milestones that were never kicked off as integration streams.
