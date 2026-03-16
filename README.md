# ProMat – Enterprise AI Project Management

## Overview

**Stručný popis:** Interný systém na správu projektov s úlohami, dokumentmi a rolami, ktorý umožní nahrávať PDF/DOCX a viesť nad nimi AI chat, sumarizáciou a vyhľadávaním. Všetko beží lokálne bez odosielania dát tretím stranám.

**Cieľ projektu:** Prepojiť databázový projektový manažment s inteligentnou prácou s dokumentami tak, aby tím vedel v jednom nástroji plánovať, ukladať a priebežne vyťahovať kľúčové informácie z príloh cez kontextový chat. Systém má zvýšiť prehľad, skrátiť čas hľadania informácií a vytvoriť auditovateľné rozhodovanie s odkazmi na zdroje.

---

## Architecture

| Layer | Technology |
|---|---|
| Frontend | Jinja2 templates + Tailwind CSS (CDN) + vanilla JS |
| Backend | Python 3.11+ / Flask |
| Database | SQLite (via SQLAlchemy ORM) |
| File storage | Local filesystem (`uploads/`) |
| AI / LLM | Ollama (local) – **implemented by project owner** |

**Design reference:** `template.html` – dark-mode-first, Space Grotesk font, Material Symbols icons, Tailwind CSS utility classes, fully responsive (mobile-first breakpoints).

---

## Key Features

- **Projects & Tasks:** CRUD projects, kanban lists, tasks with deadlines, assignees, comments, status & priority
- **Documents:** Upload PDF/DOCX, automatic text extraction, versioning, tags
- **AI Chat over Documents:** Q&A with passage citations, document summarization, term search *(AI logic implemented by owner)*
- **Roles & Permissions:** admin, owner, advocate, koncipient, secretariat
- **Dashboard:** Real-time stats, project progress, recent tasks, AI insights feed, recent documents

---

## Project Structure (Target)

```
ProMAT/
├── README.md                    # This file – plan & progress tracker
├── template.html                # Design reference (read-only)
├── requirements.txt             # Python dependencies
├── config.py                    # App configuration (SECRET_KEY, DB URI, upload path)
├── run.py                       # Entry point – `python run.py`
├── app/
│   ├── __init__.py              # Flask app factory, register blueprints
│   ├── extensions.py            # SQLAlchemy, LoginManager, CSRFProtect instances
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # User model (roles, auth)
│   │   ├── project.py           # Project model
│   │   ├── task.py              # Task model (status, priority, assignee)
│   │   ├── document.py          # Document model (file metadata, extracted text)
│   │   ├── comment.py           # Comment model (on tasks)
│   │   └── ai_chat.py           # AI chat session & message models
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── auth.py              # Login, logout, register routes
│   │   ├── dashboard.py         # Dashboard route (main page)
│   │   ├── projects.py          # Project CRUD routes
│   │   ├── tasks.py             # Task CRUD + kanban routes
│   │   ├── documents.py         # Document upload, list, detail routes
│   │   ├── ai_chat.py           # AI chat routes (stub endpoints for owner)
│   │   └── team.py              # Team / user management routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_service.py  # PDF/DOCX text extraction logic
│   │   └── ai_service.py        # AI stub service (owner fills in)
│   ├── templates/
│   │   ├── base.html            # Base layout (sidebar, header, footer)
│   │   ├── components/
│   │   │   ├── sidebar.html     # Sidebar navigation partial
│   │   │   ├── header.html      # Top header partial
│   │   │   ├── footer.html      # Footer partial
│   │   │   ├── stats_card.html  # Reusable stat card component
│   │   │   ├── project_row.html # Project progress row component
│   │   │   ├── task_row.html    # Task table row component
│   │   │   ├── document_card.html # Document list item component
│   │   │   ├── ai_insight.html  # AI insight feed item component
│   │   │   └── modal.html       # Generic modal component
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── dashboard/
│   │   │   └── index.html       # Dashboard page (matches template.html)
│   │   ├── projects/
│   │   │   ├── list.html
│   │   │   ├── detail.html
│   │   │   └── form.html        # Create/Edit project form
│   │   ├── tasks/
│   │   │   ├── list.html        # Task table view
│   │   │   ├── kanban.html      # Kanban board view
│   │   │   └── form.html        # Create/Edit task form
│   │   ├── documents/
│   │   │   ├── list.html
│   │   │   ├── detail.html      # Document detail + extracted text
│   │   │   └── upload.html
│   │   ├── ai_chat/
│   │   │   └── index.html       # AI chat interface
│   │   └── team/
│   │       ├── list.html
│   │       └── form.html        # Invite / edit member
│   └── static/
│       ├── css/
│       │   └── custom.css       # Any custom styles beyond Tailwind
│       └── js/
│           ├── main.js          # Sidebar toggle, dark mode, global handlers
│           ├── kanban.js        # Drag-and-drop kanban logic
│           └── chat.js          # AI chat UI interactions (fetch API)
└── uploads/                     # Uploaded documents (gitignored)
```

---

## Implementation Plan – Task List

> **Instructions for AI agents:** Pick a task, mark it `🔄 IN PROGRESS` with your agent name, complete it, then mark it `✅ DONE` with a short summary of what was created/changed. Do not skip dependencies.

### Phase 0: Project Bootstrap

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 0.1 | Create `requirements.txt` (Flask, SQLAlchemy, Flask-Login, Flask-WTF, python-docx, PyPDF2, Werkzeug) | ✅ DONE | GitHub Copilot | Added core Flask stack and document-processing dependencies |
| 0.2 | Create `config.py` with `SECRET_KEY`, `SQLALCHEMY_DATABASE_URI` (sqlite:///promat.db), `UPLOAD_FOLDER`, `MAX_CONTENT_LENGTH` | ✅ DONE | GitHub Copilot | Added config with env overrides and safe local defaults |
| 0.3 | Create `run.py` entry point that calls `create_app()` and runs dev server | ✅ DONE | GitHub Copilot | Added app entrypoint with debug run block |
| 0.4 | Create `app/__init__.py` – Flask app factory, register extensions & blueprints | ✅ DONE | GitHub Copilot | Added app factory, upload dir creation, and full blueprint registration |
| 0.5 | Create `app/extensions.py` – instantiate SQLAlchemy, LoginManager, CSRFProtect | ✅ DONE | GitHub Copilot | Added extension singletons for db/login/csrf |

### Phase 1: Database Models

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 1.1 | Create `app/models/user.py` – User model: id, username, email, password_hash, role (enum: admin/owner/advocate/koncipient/secretariat), created_at, `UserMixin` | ✅ DONE | GitHub Copilot | Added `User` model with role enum, timestamps, and core relationships |
| 1.2 | Create `app/models/project.py` – Project model: id, name, description, status (active/archived/completed), progress percentage, owner_id (FK→User), created_at, updated_at | ✅ DONE | GitHub Copilot | Added `Project` model with status enum, owner FK, progress, and timestamps |
| 1.3 | Create `app/models/task.py` – Task model: id, title, description, status (todo/in_progress/in_review/done), priority (low/medium/high/critical), progress, project_id (FK→Project), assignee_id (FK→User), due_date, created_at | ✅ DONE | GitHub Copilot | Added `Task` model with status/priority enums and project/assignee links |
| 1.4 | Create `app/models/document.py` – Document model: id, filename, original_name, file_type (pdf/docx), file_size, extracted_text, tags (JSON), project_id (FK→Project), uploaded_by (FK→User), version, created_at | ✅ DONE | GitHub Copilot | Added `Document` model with metadata, JSON tags, and uploader/project relations |
| 1.5 | Create `app/models/comment.py` – Comment model: id, content, task_id (FK→Task), author_id (FK→User), created_at | ✅ DONE | GitHub Copilot | Added `Comment` model linked to tasks and users |
| 1.6 | Create `app/models/ai_chat.py` – ChatSession model: id, title, document_id (FK→Document, nullable), user_id (FK→User), created_at. ChatMessage model: id, session_id (FK→ChatSession), role (user/assistant), content, citations (JSON), created_at | ✅ DONE | GitHub Copilot | Added `ChatSession`/`ChatMessage` models with enum role and JSON citations |
| 1.7 | Create `app/models/__init__.py` – import all models, create `init_db()` function that calls `db.create_all()` | ✅ DONE | GitHub Copilot | Added model exports and `init_db()` helper; integrated into app startup |

### Phase 2: Base Templates & Layout (Responsive + Modular)

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 2.1 | Create `app/templates/base.html` – full page skeleton matching `template.html` design: dark mode classes, Tailwind CDN, Space Grotesk font, Material Symbols. Must include `{% block content %}`, mobile hamburger menu toggle, responsive sidebar (hidden on mobile, slide-in overlay). Wire up `{% include %}` for sidebar, header, footer | ✅ DONE | GitHub Copilot | Added dark-mode-first base shell with Tailwind config and include blocks |
| 2.2 | Create `app/templates/components/sidebar.html` – sidebar nav partial. Highlight active page via `request.endpoint`. Links: Dashboard, Projects, Tasks, Documents, AI Chat, Team, Settings. Bottom: New Project button. On mobile: full-screen overlay with close button | ✅ DONE | GitHub Copilot | Added responsive sidebar with endpoint-aware active states and mobile overlay |
| 2.3 | Create `app/templates/components/header.html` – top header bar: hamburger button (mobile only, `md:hidden`), search input, notifications bell, user profile (from `current_user`). Responsive: hide user name on small screens | ✅ DONE | GitHub Copilot | Added responsive header with mobile menu trigger and notifications dropdown |
| 2.4 | Create `app/templates/components/footer.html` – footer bar matching template design | ✅ DONE | GitHub Copilot | Added shared footer consistent with reference styling |
| 2.5 | Create `app/templates/components/stats_card.html` – macro/include for stat cards (title, value, icon, trend). Used on dashboard | ✅ DONE | GitHub Copilot | Added reusable stats card macro |
| 2.6 | Create `app/templates/components/project_row.html` – macro for project progress row (name, progress bar, team avatars, due date badge) | ✅ DONE | GitHub Copilot | Added reusable project progress row macro |
| 2.7 | Create `app/templates/components/task_row.html` – macro for task table row (name, owner, status badge, progress) | ✅ DONE | GitHub Copilot | Added reusable task row macro with status badge mapping |
| 2.8 | Create `app/templates/components/document_card.html` – macro for document list item (icon by file type, name, modified date) | ✅ DONE | GitHub Copilot | Added reusable document card macro with file-type icon styles |
| 2.9 | Create `app/templates/components/ai_insight.html` – macro for AI insight feed item (type badge, title, description, timestamp, action button) | ✅ DONE | GitHub Copilot | Added reusable AI insight feed macro |
| 2.10 | Create `app/templates/components/modal.html` – generic modal component (title, body block, footer with cancel/confirm buttons). Trigger via JS `data-modal-target` | ✅ DONE | GitHub Copilot | Added generic modal macro with data-attribute hooks |
| 2.11 | Create `app/static/css/custom.css` – sidebar active state style, scrollbar styling, any transitions not handled by Tailwind | ✅ DONE | GitHub Copilot | Added custom styling for active sidebar, scrollbars, and transitions |
| 2.12 | Create `app/static/js/main.js` – sidebar mobile toggle (open/close overlay), dark mode toggle (localStorage persist), modal open/close handlers, notification dropdown | ✅ DONE | GitHub Copilot | Added global UI handlers for sidebar, theme, modals, and notifications |

### Phase 3: Authentication

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 3.1 | Create `app/blueprints/auth.py` – blueprint with routes: `GET/POST /login`, `GET/POST /register`, `GET /logout`. Use Flask-Login. Password hashing via Werkzeug. After login redirect to dashboard | ✅ DONE | GitHub Copilot | Added full auth flow with Flask-Login sessions, Werkzeug hashing, and redirects |
| 3.2 | Create `app/templates/auth/login.html` – login form (email, password, remember me). Responsive centered card layout matching dark theme | ✅ DONE | GitHub Copilot | Added centered dark-themed login template with remember-me field |
| 3.3 | Create `app/templates/auth/register.html` – register form (username, email, password, confirm password, role select). Same styling | ✅ DONE | GitHub Copilot | Added centered dark-themed registration template with role select |

### Phase 4: Dashboard

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 4.1 | Create `app/blueprints/dashboard.py` – blueprint, `GET /` route. Query: active project count, upcoming deadline count, AI insight count (placeholder), top 3 priority projects, recent 3 tasks, recent 3 documents. Pass to template | ✅ DONE | GitHub Copilot | Added dashboard queries/aggregation and passed computed data into template |
| 4.2 | Create `app/templates/dashboard/index.html` – extends `base.html`. Replicate `template.html` layout exactly: stats grid (3 cards), 2-column layout (project tracking + task table on left, AI insights feed + recent docs on right). Use component includes/macros. Responsive: stack to single column on mobile (`lg:grid-cols-3` → `grid-cols-1`) | ✅ DONE | GitHub Copilot | Added responsive dashboard page using Phase 2 component macros and reference layout |

### Phase 5: Projects Module

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 5.1 | Create `app/blueprints/projects.py` – blueprint with routes: `GET /projects` (list), `GET/POST /projects/new` (create), `GET /projects/<id>` (detail), `GET/POST /projects/<id>/edit` (update), `POST /projects/<id>/delete` (delete). Role-based access: only admin/owner can create/delete | ✅ DONE | GitHub Copilot | Implemented full CRUD routes with login protection and admin/owner guards for create/delete |
| 5.2 | Create `app/templates/projects/list.html` – project list page: grid of project cards showing name, description, progress bar, status badge, member count. Responsive grid (`md:grid-cols-2 lg:grid-cols-3`). Search/filter bar at top | ✅ DONE | GitHub Copilot | Added responsive cards grid with search/status filtering UI |
| 5.3 | Create `app/templates/projects/detail.html` – project detail page: header with name & description, progress stats, tabs for Tasks / Documents / Team. Each tab loads relevant filtered list | ✅ DONE | GitHub Copilot | Added detail view with tabbed tasks/documents/team sections and project stats |
| 5.4 | Create `app/templates/projects/form.html` – create/edit project form (name, description, status). Responsive form layout, dark-themed inputs matching template design | ✅ DONE | GitHub Copilot | Added shared responsive create/edit project form template |

### Phase 6: Tasks Module

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 6.1 | Create `app/blueprints/tasks.py` – blueprint with routes: `GET /tasks` (list all), `GET /tasks/kanban` (kanban view), `GET/POST /tasks/new` (create), `GET /tasks/<id>` (detail), `GET/POST /tasks/<id>/edit` (update), `POST /tasks/<id>/delete`, `POST /tasks/<id>/status` (AJAX status update for kanban), `POST /tasks/<id>/comment` (add comment) | ✅ DONE | GitHub Copilot | Implemented full task CRUD, filters, kanban endpoint, AJAX status update, and comments routes |
| 6.2 | Create `app/templates/tasks/list.html` – task table view matching template's "Recent Task Activity" table style. Columns: task name, owner, status badge, progress. Filter by project, status, assignee. Toggle to kanban view | ✅ DONE | GitHub Copilot | Added responsive filtered task table view with kanban toggle |
| 6.3 | Create `app/templates/tasks/kanban.html` – kanban board: 4 columns (To Do, In Progress, In Review, Done). Cards show task title, assignee avatar, priority badge, due date. Drag-and-drop between columns via JS | ✅ DONE | GitHub Copilot | Added 4-column drag-and-drop kanban board with status lanes |
| 6.4 | Create `app/templates/tasks/form.html` – create/edit task form (title, description, project select, assignee select, priority select, due date, status). Responsive layout | ✅ DONE | GitHub Copilot | Added responsive create/edit task form with comment section on edit |
| 6.5 | Create `app/static/js/kanban.js` – drag-and-drop logic: HTML5 Drag & Drop API. On drop, send `POST /tasks/<id>/status` via fetch to update status. Animate card movement | ✅ DONE | GitHub Copilot | Added drag-drop logic and fetch POST status updates for kanban cards |

### Phase 7: Documents Module

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 7.1 | Create `app/services/document_service.py` – functions: `extract_text_from_pdf(filepath)` using PyPDF2, `extract_text_from_docx(filepath)` using python-docx, `process_upload(file, project_id, user_id)` – saves file, extracts text, creates Document record | ✅ DONE | GitHub Copilot | Added upload service with PDF/DOCX text extraction and DB persistence |
| 7.2 | Create `app/blueprints/documents.py` – blueprint with routes: `GET /documents` (list), `GET/POST /documents/upload` (upload form + handler), `GET /documents/<id>` (detail with extracted text), `GET /documents/<id>/download` (file download), `POST /documents/<id>/delete`. Filter by project, file type, tags | ✅ DONE | GitHub Copilot | Implemented full documents routes with filtering, upload, detail, download, and delete |
| 7.3 | Create `app/templates/documents/list.html` – document list page matching "Recent Documents" card style from template. File type icon (PDF=red, DOCX=blue), name, upload date, uploader. Grid/list toggle. Search bar | ✅ DONE | GitHub Copilot | Added responsive list page with search/filter controls and grid/list view toggle |
| 7.4 | Create `app/templates/documents/detail.html` – document detail: file metadata (name, size, type, uploader, date), extracted text display in scrollable container, tags, link to AI chat, download button | ✅ DONE | GitHub Copilot | Added detail page with metadata panel, extracted text view, and actions |
| 7.5 | Create `app/templates/documents/upload.html` – upload form: drag-and-drop zone + file input, project select, tags input. Show upload progress. Accepted: .pdf, .docx | ✅ DONE | GitHub Copilot | Added drag-drop upload form with accepted file constraints and progress bar |

### Phase 8: AI Chat Module (Stubs for Owner)

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 8.1 | Create `app/services/ai_service.py` – stub service class `AIService` with methods: `chat(session_id, message, context) → str`, `summarize(text) → str`, `search_terms(query, documents) → list`. Each returns placeholder text like `"[AI response placeholder – implement with Ollama]"`. Clear docstrings explaining expected input/output | ✅ DONE | GitHub Copilot | Added `AIService` placeholder implementation with documented stub methods |
| 8.2 | Create `app/blueprints/ai_chat.py` – blueprint with routes: `GET /ai-chat` (chat interface, list sessions), `POST /ai-chat/sessions` (create new session), `GET /ai-chat/sessions/<id>` (load session messages), `POST /ai-chat/sessions/<id>/message` (send message – JSON API, calls `AIService.chat()`), `POST /ai-chat/summarize/<doc_id>` (summarize document) | ✅ DONE | GitHub Copilot | Implemented AI chat routes for sessions, messages JSON API, and summarize endpoint |
| 8.3 | Create `app/templates/ai_chat/index.html` – chat interface: left sidebar with session list, main area with message history (user messages right-aligned, AI left-aligned with citations), bottom input bar with send button. Matches template's AI Insights gradient styling. Responsive: session list collapses to dropdown on mobile | ✅ DONE | GitHub Copilot | Added responsive AI chat page with session sidebar, message stream, and composer |
| 8.4 | Create `app/static/js/chat.js` – chat UI logic: send message via fetch POST, append user message immediately, show typing indicator, append AI response. Auto-scroll to bottom. New session creation. Load session history on click | ✅ DONE | GitHub Copilot | Added frontend chat logic with optimistic append, typing state, summarize action, and autoscroll |

### Phase 9: Team & Roles Module

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 9.1 | Create `app/blueprints/team.py` – blueprint with routes: `GET /team` (list all users with roles), `GET/POST /team/<id>/edit` (edit user role – admin only), `POST /team/<id>/delete` (remove user – admin only). Show member's assigned projects and tasks count | ✅ DONE | GitHub Copilot | Implemented team list plus admin-only role edit/delete routes with workload stats |
| 9.2 | Create `app/templates/team/list.html` – team list page: table/cards showing username, email, role badge, project count, joined date. Admin sees edit/delete actions | ✅ DONE | GitHub Copilot | Added responsive team member table with admin action controls |
| 9.3 | Create `app/templates/team/form.html` – edit user form: role select dropdown. Only accessible by admin role | ✅ DONE | GitHub Copilot | Added admin role-edit form template |
| 9.4 | Implement role-based access decorator `@role_required(*roles)` in `app/blueprints/__init__.py` – reusable decorator that checks `current_user.role` and returns 403 if not authorized | ✅ DONE | GitHub Copilot | Added reusable `role_required` decorator integrated with Flask-Login |

### Phase 10: Integration, Polish & Seed Data

| # | Task | Status | Agent | Notes |
|---|------|--------|-------|-------|
| 10.1 | Register all blueprints in `app/__init__.py` with correct URL prefixes. Ensure `init_db()` is called on first run. Configure Flask-Login `login_view` | ✅ DONE | GitHub Copilot | Verified blueprint registration, URL prefixes, `init_db()` startup call, and `login_view` config |
| 10.2 | Create `seed.py` – script to populate DB with sample data: 2 users (admin + member), 3 projects, 5 tasks, 2 documents (create dummy text entries), 1 AI chat session with 2 messages | ✅ DONE | GitHub Copilot | Added idempotent `seed.py` that populates users, projects, tasks, documents, and chat seed data |
| 10.3 | Add flash message display to `base.html` – success/error/info notifications styled as toast-like alerts | ✅ DONE | GitHub Copilot | Added fixed-position toast-style flash message stack to base layout |
| 10.4 | Add 404 and 500 error page templates (`app/templates/errors/404.html`, `app/templates/errors/500.html`) with consistent styling. Register error handlers in app factory | ✅ DONE | GitHub Copilot | Added custom error templates and registered app-level error handlers |
| 10.5 | Final responsive QA pass – ensure all pages work on mobile (≤640px), tablet (≤1024px), and desktop. Sidebar collapses, grids stack, tables scroll horizontally, modals are full-width on mobile | ✅ DONE | GitHub Copilot | Performed responsive class audit and route/template smoke checks across core modules |
| 10.6 | Create `.gitignore` (uploads/, *.db, __pycache__/, .env, venv/) | ✅ DONE | GitHub Copilot | Added `.gitignore` with required local artifact/environment exclusions |

### Phase 11: Jira/Trello Feature Parity Backlog

| # | Task | Priority | Complexity | Dependencies | Status | Agent | Notes |
|---|------|----------|------------|--------------|--------|-------|-------|
| 11.1 | Task detail page: rich description, edit history, assignee timeline, related links | High | M | 6.1, 6.4 | ✅ DONE | GitHub Copilot | Added dedicated task detail page with inline editing, links, and activity timeline |
| 11.2 | In-place task editing (title, description, assignee, status, priority, due date) from detail and board views | High | M | 11.1, 6.3 | ✅ DONE | GitHub Copilot | Completed board-side in-card editor on Kanban with quick-update API save + status-column sync |
| 11.3 | Subtasks and checklist items with completion progress rollup to parent task | High | L | 11.1 | ✅ DONE | GitHub Copilot | Added checklist item add/toggle/delete with completion counter on task detail |
| 11.4 | Labels/tags system with color coding and multi-label filtering | Medium | M | 6.1, 6.2 | ✅ DONE | GitHub Copilot | Added task labels, labels persistence, and list/kanban label display + list filtering |
| 11.5 | Task dependencies (blocks/is blocked by) and dependency-aware status validation | Medium | L | 11.1, 11.2 | ✅ DONE | GitHub Copilot | Added blocker links with cycle prevention and status guard for blocked tasks |
| 11.6 | Comment threads with @mentions and per-comment edit/delete permissions | High | M | 6.1 | ✅ DONE | GitHub Copilot | Added mention highlighting and comment edit/delete permissions (author/admin/owner) |
| 11.7 | Attachment management on tasks (upload, preview, version notes) | Medium | M | 7.1, 7.2 | ✅ DONE | GitHub Copilot | Added task attachment model and detail UI with upload, preview, download, delete, and version notes |
| 11.8 | Activity timeline (who changed what/when) for tasks and projects | Medium | M | 11.1, 11.2, 11.6 | ✅ DONE | GitHub Copilot | Added per-task activity log across updates, comments, checklist, labels, and dependencies |
| 11.9 | Backlog + Sprint planning (create sprint, move tasks, start/close sprint) | Medium | L | 11.2, 11.3, 11.4 | ✅ DONE | GitHub Copilot | Added sprint model/routes/pages with backlog assignment and sprint status lifecycle |
| 11.10 | Advanced board controls: custom columns, WIP limits, swimlanes by assignee/project | Medium | L | 6.3, 11.2 | ✅ DONE | GitHub Copilot | Added per-project board settings for custom column labels, WIP limits, and swimlane modes |
| 11.11 | Saved filters and quick views (My Tasks, Overdue, Due This Week, High Priority) | Medium | M | 6.2, 11.4 | ✅ DONE | GitHub Copilot | Added quick-view presets and persisted user saved filters in task list |
| 11.12 | Bulk actions for tasks (assign, status change, label, delete) | Medium | M | 6.2, 11.4 | ✅ DONE | GitHub Copilot | Added multi-select bulk operations with assignment/status/label/delete actions |
| 11.13 | Notification center + email/in-app notifications for mentions, assignments, due dates | High | L | 11.2, 11.6, 11.8 | ✅ DONE | GitHub Copilot | Implemented notification center and dual-channel notification records for assignment/mentions/due reminders |
| 11.14 | Watchers/followers on tasks/projects with unsubscribe controls | Low | M | 11.1, 11.13 | ✅ DONE | GitHub Copilot | Added task/project watch toggles, watcher lists, and unsubscribe behavior |
| 11.15 | Reporting: burndown, cycle time, throughput, completion trends | Medium | L | 11.3, 11.8, 11.9 | ✅ DONE | GitHub Copilot | Added reporting page with burndown, throughput, cycle-time estimate, and 7-day completion trend |
| 11.16 | Import/Export and Integrations: CSV import/export, webhook endpoints, basic API tokens | Low | L | 11.1, 11.8 | ✅ DONE | GitHub Copilot | Added CSV import/export, token-based webhook endpoint, and API token management UI |
| 11.17 | Granular permissions matrix per project (viewer/member/manager/admin) | High | L | 9.4, 11.6, 11.13 | ✅ DONE | GitHub Copilot | Added project membership role matrix and role-gated task/project write operations |
| 11.18 | Automation rules (if/then triggers for status, assignment, labels, due reminders) | Medium | XL | 11.2, 11.4, 11.8, 11.13 | ✅ DONE | GitHub Copilot | Added configurable project automation rules and task-update rule execution hooks |

### Phase 12+: Implementation Streams

| # | Stream Milestone | Priority | Complexity | Dependencies | Status | Agent | Notes |
|---|------------------|----------|------------|--------------|--------|-------|-------|
| 12.1 | **Task Core**: Deliver task detail, in-place editing, subtasks/checklists, labels | High | L | 11.1–11.4 | ✅ DONE | GitHub Copilot | Completed task core vertical slice: parent-child subtasks, checklist create/edit/toggle/delete, inline task detail autosave, chip-based label editing with suggestions/autocomplete, hierarchy filtering, bulk/webhook subtask constraints, parent progress rollup with auto-close/auto-reopen, live rollup/status refresh in kanban, and linking/unlinking project documents directly on tasks |
| 12.2 | **Collaboration**: Deliver mentions, attachments, activity timeline, notifications, watchers | High | L | 11.6–11.8, 11.13–11.14 | ✅ DONE | GitHub Copilot | Completed collaboration hardening by enforcing project-membership authorization on documents/projects visibility + watcher operations and preserving existing mentions/attachments/timeline/notifications feature set |
| 12.3 | **Planning**: Deliver dependency graph, backlog/sprint planning, advanced board controls | Medium | XL | 11.5, 11.9, 11.10 | ✅ DONE | GitHub Copilot | Completed planning stream with dependency graph visualization on task detail, story-points planning model, and sprint velocity/burndown point metrics in reports while retaining backlog/sprint and advanced board controls |
| 12.4 | **Governance**: Deliver granular permissions matrix and admin tooling | High | L | 11.17 | ✅ DONE | GitHub Copilot | Completed governance stream with admin module (dashboard + audit log + permission CSV export), audit log model/service, role-gated admin navigation, and audit instrumentation for user/project/document governance actions |
| 12.5 | **Scale & Insights**: Deliver saved filters, bulk actions, reporting, import/export, automation | Medium | XL | 11.11, 11.12, 11.15, 11.16, 11.18 | ✅ DONE | GitHub Copilot | Completed stream with saved filters (including hierarchy mode), atomic bulk actions with rollback and subtask guards, expanded reporting (velocity + story points + burndown points), CSV import/export + webhook/API token integrations, and active automation rules wired into task updates |

### Roadmap Conventions

- Phases **0–10** are historical and already implemented.
- Phases **11+** are planned roadmap work and should start as `⬜ TODO`, then move to `🔄 IN PROGRESS`, then `✅ DONE`.
- For Phases **11+**, always fill `Complexity` and `Dependencies` before starting implementation.
- Use balanced prioritization: mix foundational items with strategic capabilities in each release slice.

---

## Design Guidelines (from `template.html`)

All pages **must** follow these rules:

- **Dark mode first:** `<html class="dark">`, use `dark:` Tailwind prefixes everywhere
- **Colors:** primary `#197fe6`, bg-dark `#111921`, surface-dark `#1b252e`, border-dark `#293038`
- **Font:** Space Grotesk (Google Fonts CDN)
- **Icons:** Material Symbols Outlined (Google Fonts CDN)
- **Border radius:** default `0.25rem`, lg `0.5rem`, xl `0.75rem`
- **Cards:** `bg-white dark:bg-surface-dark rounded-xl border border-slate-200 dark:border-border-dark shadow-sm`
- **Active sidebar item:** `background-color: #293038; border-right: 3px solid #197fe6;`
- **Status badges:** blue = In Review, amber = Pending, emerald = Complete, red = Critical
- **Responsive breakpoints:** `sm:` (640px), `md:` (768px), `lg:` (1024px), `xl:` (1280px)
- **Mobile sidebar:** hidden by default, toggled via hamburger button as full-screen overlay
- **Tables:** horizontally scrollable on mobile (`overflow-x-auto`)
- **Grids:** collapse from multi-column to single column on mobile

## AI Integration Points (For Owner)

The following files contain stubs/placeholders that the owner will fill in with Ollama-based AI logic:

1. **`app/services/ai_service.py`** – Core AI logic:
   - `chat()` – RAG-based Q&A over document text with citation extraction
   - `summarize()` – Document summarization
   - `search_terms()` – Semantic term search across documents
2. **`app/blueprints/ai_chat.py`** – Endpoints already wired to call `AIService` methods
3. **`app/templates/ai_chat/index.html`** – Chat UI already built, sends/receives JSON
4. **`app/static/js/chat.js`** – Frontend fetch calls already implemented

**Expected AI flow:**
1. User uploads document → text extracted and stored in DB
2. User opens AI Chat → selects document context (or all project docs)
3. User sends message → backend passes message + document text to LLM
4. LLM returns answer with citations → displayed in chat UI

---

## Progress Log

| Date | Agent | Task(s) | Summary |
|------|-------|---------|---------|
| 2026-02-23 | GitHub Copilot | 0.1–0.5 | Bootstrapped Flask project foundation, config, app factory, extensions, and registered blueprint stubs |
| 2026-02-23 | GitHub Copilot | 1.1–1.7 | Implemented SQLAlchemy models, enums/relationships, and auto `init_db()` schema bootstrap |
| 2026-02-23 | GitHub Copilot | 2.1–2.12 | Implemented base layout, reusable template components, and global CSS/JS UI behavior |
| 2026-02-23 | GitHub Copilot | 3.1–3.3 | Implemented authentication routes and responsive dark-themed login/register templates |
| 2026-02-23 | GitHub Copilot | 4.1–4.2 | Implemented dashboard data queries and full responsive dashboard template composition |
| 2026-02-23 | GitHub Copilot | 5.1–5.4 | Implemented Projects CRUD blueprint and responsive list/detail/form templates with role-based management |
| 2026-02-23 | GitHub Copilot | 6.1–6.5 | Implemented Tasks CRUD + kanban/status updates, list/kanban/form templates, and drag-drop JS |
| 2026-02-23 | GitHub Copilot | 7.1–7.5 | Implemented document extraction/upload services, documents routes, and list/detail/upload templates |
| 2026-02-23 | GitHub Copilot | 8.1–8.4 | Implemented AI service stubs, AI chat endpoints, chat interface template, and frontend chat interactions |
| 2026-02-23 | GitHub Copilot | 9.1–9.4 | Implemented team management routes/templates and reusable role-based access decorator |
| 2026-02-23 | GitHub Copilot | 10.1–10.6 | Finalized integration/polish: error handlers/pages, flash toasts, seed script, `.gitignore`, and final QA checks |
| 2026-02-23 | GitHub Copilot | README roadmap extension | Added Jira/Trello parity Phase 11 backlog + Phase 12+ implementation streams with complexity/dependency tracking |
| 2026-02-23 | GitHub Copilot | 11.1–11.6, 11.8 | Started Phase 11: added task detail workspace, quick edit API, checklist, labels/filtering, dependencies guard, mentions + comment permissions, and activity timeline |
| 2026-02-23 | GitHub Copilot | 11.7 | Implemented task attachment management (upload/preview/download/delete), version notes, and activity logging |
| 2026-02-23 | GitHub Copilot | 11.2 (board) | Added in-card Kanban editor for title/description/assignee/priority/status/due/progress using `/tasks/<id>/quick-update` |
| 2026-02-23 | GitHub Copilot | 11.9–11.18 | Completed remaining Phase 11 scope: sprints/backlog planning, board controls, saved filters, bulk actions, notifications/watchers, reporting, CSV/webhooks/API tokens, permissions matrix, and automation rules |

---

## How to Run

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python run.py

# 4. (Optional) Seed sample data
python seed.py

# 5. Open browser
# http://localhost:5000
```