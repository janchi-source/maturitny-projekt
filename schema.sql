-- Auto-generated from SQLAlchemy models
-- Dialect: SQLite
PRAGMA foreign_keys=OFF;


CREATE TABLE managed_roles (
	id INTEGER NOT NULL, 
	"key" VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	rights JSON NOT NULL, 
	is_system BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE ("key")
);


CREATE TABLE role_label_settings (
	id INTEGER NOT NULL, 
	role_value VARCHAR(50) NOT NULL, 
	label VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (role_value)
);


CREATE TABLE task_labels_master (
	id INTEGER NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	color VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);


CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(11) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
);


CREATE TABLE api_tokens (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	token VARCHAR(80) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	last_used_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (token)
);


CREATE TABLE notifications (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	channel VARCHAR(30) NOT NULL, 
	kind VARCHAR(50) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	message TEXT NOT NULL, 
	is_read BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE projects (
	id INTEGER NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	description TEXT, 
	status VARCHAR(9) NOT NULL, 
	progress INTEGER NOT NULL, 
	owner_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE task_saved_filters (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	project_id INTEGER, 
	status VARCHAR(30), 
	assignee_id INTEGER, 
	label VARCHAR(80), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE user_managed_roles (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_managed_role_user UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES managed_roles (id) ON DELETE CASCADE
);


CREATE TABLE automation_rules (
	id INTEGER NOT NULL, 
	project_id INTEGER NOT NULL, 
	trigger_type VARCHAR(40) NOT NULL, 
	condition_value VARCHAR(120), 
	action_type VARCHAR(40) NOT NULL, 
	action_value VARCHAR(255), 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);


CREATE TABLE documents (
	id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	original_name VARCHAR(255) NOT NULL, 
	file_type VARCHAR(4) NOT NULL, 
	file_size INTEGER NOT NULL, 
	extracted_text TEXT, 
	tags JSON NOT NULL, 
	project_id INTEGER NOT NULL, 
	uploaded_by INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(uploaded_by) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE project_memberships (
	id INTEGER NOT NULL, 
	project_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	role VARCHAR(7) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_project_membership UNIQUE (project_id, user_id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE watchers (
	id INTEGER NOT NULL, 
	project_id INTEGER, 
	task_id INTEGER, 
	user_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_project_watcher UNIQUE (project_id, user_id), 
	CONSTRAINT uq_task_watcher UNIQUE (task_id, user_id), 
	CONSTRAINT ck_watcher_target CHECK ((project_id IS NOT NULL AND task_id IS NULL) OR (project_id IS NULL AND task_id IS NOT NULL)), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE sprints (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	goal TEXT, 
	status VARCHAR(7) NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	project_id INTEGER NOT NULL, 
	created_by INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
);


CREATE TABLE task_board_settings (
	id INTEGER NOT NULL, 
	project_id INTEGER NOT NULL, 
	todo_label VARCHAR(80) NOT NULL, 
	in_progress_label VARCHAR(80) NOT NULL, 
	in_review_label VARCHAR(80) NOT NULL, 
	done_label VARCHAR(80) NOT NULL, 
	wip_todo INTEGER, 
	wip_in_progress INTEGER, 
	wip_in_review INTEGER, 
	wip_done INTEGER, 
	swimlane_mode VARCHAR(30) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (project_id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);


CREATE TABLE chat_sessions (
	id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	document_id INTEGER, 
	user_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE tasks (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	status VARCHAR(11) NOT NULL, 
	priority VARCHAR(8) NOT NULL, 
	progress INTEGER NOT NULL, 
	project_id INTEGER NOT NULL, 
	sprint_id INTEGER, 
	assignee_id INTEGER, 
	due_date DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(sprint_id) REFERENCES sprints (id) ON DELETE SET NULL, 
	FOREIGN KEY(assignee_id) REFERENCES users (id) ON DELETE SET NULL
);


CREATE TABLE chat_messages (
	id INTEGER NOT NULL, 
	session_id INTEGER NOT NULL, 
	role VARCHAR(9) NOT NULL, 
	content TEXT NOT NULL, 
	citations JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
);


CREATE TABLE comments (
	id INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	task_id INTEGER NOT NULL, 
	author_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE, 
	FOREIGN KEY(author_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE task_activities (
	id INTEGER NOT NULL, 
	task_id INTEGER NOT NULL, 
	actor_id INTEGER, 
	action VARCHAR(80) NOT NULL, 
	details TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE, 
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
);


CREATE TABLE task_attachments (
	id INTEGER NOT NULL, 
	task_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	original_name VARCHAR(255) NOT NULL, 
	content_type VARCHAR(120), 
	file_size INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	version_note TEXT, 
	uploaded_by INTEGER, 
	created_at DATETIME NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE, 
	FOREIGN KEY(uploaded_by) REFERENCES users (id) ON DELETE SET NULL
);


CREATE TABLE task_checklist_items (
	id INTEGER NOT NULL, 
	task_id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	is_done BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE
);


CREATE TABLE task_dependencies (
	blocker_id INTEGER NOT NULL, 
	blocked_id INTEGER NOT NULL, 
	PRIMARY KEY (blocker_id, blocked_id), 
	FOREIGN KEY(blocker_id) REFERENCES tasks (id) ON DELETE CASCADE, 
	FOREIGN KEY(blocked_id) REFERENCES tasks (id) ON DELETE CASCADE
);


CREATE TABLE task_labels (
	task_id INTEGER NOT NULL, 
	label_id INTEGER NOT NULL, 
	PRIMARY KEY (task_id, label_id), 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE, 
	FOREIGN KEY(label_id) REFERENCES task_labels_master (id) ON DELETE CASCADE
);

PRAGMA foreign_keys=ON;
