# Next Steps (Handoff)

Date: 2026-03-16

This file captures the recommended next implementation steps after today's work.

## Current Status

Completed today:
- Task-document linking/unlinking implemented in task detail UI.
- File version-control foundation added:
  - Document revisions with SHA-256 hash.
  - Task attachment revisions with SHA-256 hash.
  - Soft delete for documents and task attachments.
  - Archived documents page + restore endpoint.
- Optimistic conflict checks (`lock_version`) added for:
  - Task document link/unlink.
  - Document archive/restore.

## Priority Next Steps

### 1. Revision-Pinned Task Linking (Highest)
Goal: allow linking a specific document revision to a task (not only latest).

Actions:
1. Extend task detail link UI to select revision per document.
2. Add backend validation for selected revision ownership and staleness.
3. Show pinned revision badge in linked-document cards.
4. Include revision in unlink/update activity details.

Target files:
- app/blueprints/tasks.py
- app/templates/tasks/detail.html

---

### 2. Document Restore UX in Detail/List
Goal: make restore flows obvious and safe for users.

Actions:
1. Add "Archived" indicator and reason/timestamp display where relevant.
2. Add optional restore action shortcuts from document-level views.
3. Improve archived filter controls (search/tag/project/type parity with active list).

Target files:
- app/templates/documents/archived.html
- app/templates/documents/list.html
- app/templates/documents/detail.html

---

### 3. Expand Optimistic Concurrency Coverage
Goal: enforce stale-write protection on all revision-sensitive mutations.

Actions:
1. Add lock/version checks for document metadata updates (when added).
2. Add lock/version checks for attachment lifecycle updates.
3. Return structured conflict responses for API/json consumers.

Target files:
- app/blueprints/documents.py
- app/blueprints/tasks.py

---

### 4. Revision History Surfaces for Attachments
Goal: provide full history visibility for task attachments.

Actions:
1. Add attachment revisions endpoint(s).
2. Add revisions UI block in task detail.
3. Add revision download controls and version note visibility.

Target files:
- app/blueprints/tasks.py
- app/templates/tasks/detail.html

---

### 5. Link History and Compliance Traceability
Goal: make task-document relationship history queryable in UI/admin.

Actions:
1. Add link history section in task detail.
2. Show who linked/unlinked + revision + timestamps.
3. Add admin-facing filter/report for link history events.

Target files:
- app/blueprints/tasks.py
- app/blueprints/admin.py
- app/templates/tasks/detail.html
- app/templates/admin/audit_log.html

---

### 6. Hardening and QA
Goal: ensure stability under multi-user concurrency.

Actions:
1. Add tests for concurrent linking/archive/restore conflicts.
2. Add tests for soft-delete visibility and restore correctness.
3. Add tests for revision record creation/hash integrity.
4. Run manual QA matrix with two user accounts and role combinations.

Target files:
- tests/* (create if missing)
- README.md (update tested scenarios)

## Suggested Execution Order for Next Session

1. Revision-pinned task linking.
2. Attachment revision history UI/endpoints.
3. Link history UI + admin visibility.
4. Remaining concurrency checks.
5. QA hardening + documentation updates.

## Definition of Done (for this stream)

- Users can link a chosen document revision to a task.
- Linked docs show pinned revision and remain historically accurate after newer uploads.
- Conflicts are blocked with clear refresh/retry messaging.
- Soft-deleted files are recoverable via UI with audit trail.
- Revision and link lifecycle events are visible in admin/audit views.
