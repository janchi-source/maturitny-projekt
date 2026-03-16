# ProMat Bug Tracker (Verified Issues)

Last updated: 2026-03-16

This file tracks confirmed bugs or non-working UI flows observed in the current codebase.

## Open Bugs

### BUG-001 - Settings navigation does not work
- Severity: Medium
- Status: Resolved (2026-03-16)
- Area: Navigation / Sidebar
- Reproduction:
1. Log in.
2. Click Settings in the left sidebar.
- Expected:
- User is redirected to a settings page.
- Actual:
- Link points to `#`, no route is loaded.
- Evidence:
- Sidebar uses placeholder link in app/templates/components/sidebar.html.
- Affected file:
- app/templates/components/sidebar.html
- Suggested fix:
- Create a settings blueprint + template (for example /settings), then replace the placeholder href with url_for.
- Resolution:
- Added settings blueprint route and page (`/settings/`) and wired sidebar link to `url_for('settings.index')`.
- Implemented in:
- app/blueprints/settings.py
- app/templates/settings/index.html
- app/templates/components/sidebar.html
- app/__init__.py

### BUG-002 - Sign out is not accessible from UI
- Severity: High
- Status: Resolved (2026-03-16)
- Area: Authentication / Header
- Reproduction:
1. Log in.
2. Try to find a logout/sign-out action in header/sidebar/profile controls.
- Expected:
- A visible Sign out action is available.
- Actual:
- No logout link or button exists in templates.
- Evidence:
- Logout route exists in auth blueprint, but no template references auth.logout.
- Affected files:
- app/blueprints/auth.py
- app/templates/components/header.html
- app/templates/components/sidebar.html
- Suggested fix:
- Add a logout button (POST form preferred) in header profile menu or sidebar footer and wire to auth.logout.
- Resolution:
- Added visible Sign Out action in sidebar footer and on settings page, both wired to `auth.logout`.
- Implemented in:
- app/templates/components/sidebar.html
- app/templates/settings/index.html

### BUG-003 - Header search bar is visual only
- Severity: Low
- Status: Resolved (2026-03-16)
- Area: Header UX
- Reproduction:
1. Type text in header search.
2. Press Enter.
- Expected:
- Search performs global/project/task/document query.
- Actual:
- Input has no action, route, or JS handler.
- Evidence:
- Search input in header has no form submit target and no JS binding.
- Affected file:
- app/templates/components/header.html
- Suggested fix:
- Add a search endpoint and wrap input in a form, or attach JS handler for live search.
- Resolution:
- Added global search route and results page, then wrapped header search input in a real GET form.
- Implemented in:
- app/blueprints/dashboard.py
- app/templates/dashboard/search.html
- app/templates/components/header.html

### BUG-004 - Header notification dropdown is static placeholder
- Severity: Medium
- Status: Resolved (2026-03-16)
- Area: Notifications UX
- Reproduction:
1. Trigger notifications (assignment/mentions/due reminders).
2. Click bell icon in header.
- Expected:
- Dropdown shows actual latest notifications.
- Actual:
- Dropdown always shows static placeholder text.
- Evidence:
- Header template hardcodes "No new notifications".
- Affected files:
- app/templates/components/header.html
- app/static/js/main.js
- Suggested fix:
- Populate dropdown from notification query (server render or API fetch), include unread count and links.
- Resolution:
- Added app-wide context processor for recent in-app notifications and unread count, and updated header dropdown to render real notification items with link to notification center.
- Implemented in:
- app/__init__.py
- app/templates/components/header.html

## Notes
- Some backend routes for related features already exist (for example /auth/logout and /tasks/notifications), but corresponding UI wiring is missing or incomplete.
- This file currently includes only issues verified from code and navigation behavior; additional runtime test issues can be appended after QA pass.
