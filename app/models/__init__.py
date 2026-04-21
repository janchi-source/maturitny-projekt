from ..extensions import db
from .ai_chat import ChatMessage, ChatMessageRole, ChatSession
from .comment import Comment
from .document import Document, DocumentType
from .planning import (
    ApiToken,
    AutomationRule,
    Notification,
    ProjectMembership,
    ProjectMembershipRole,
    Sprint,
    SprintStatus,
    TaskBoardSetting,
    TaskSavedFilter,
    Watcher,
)
from .project import Project, ProjectStatus
from .task import Task, TaskActivity, TaskAttachment, TaskChecklistItem, TaskLabel, TaskPriority, TaskStatus
from .user import (
    ManagedRole,
    ROLE_RIGHTS,
    RoleLabelSetting,
    User,
    UserManagedRole,
    UserRole,
    ensure_default_managed_roles,
    get_effective_role_rights,
    normalize_role_rights,
    user_has_right,
)


def init_db():
    db.create_all()
    _ensure_legacy_schema_updates()
    ensure_default_managed_roles()


def _ensure_legacy_schema_updates():
    try:
        columns = db.session.execute(db.text("PRAGMA table_info(tasks)")).fetchall()
    except Exception:
        return

    existing = {str(column[1]).lower() for column in columns}
    if "sprint_id" not in existing:
        db.session.execute(db.text("ALTER TABLE tasks ADD COLUMN sprint_id INTEGER"))
        db.session.commit()

    old_to_new = {
        "owner": "leader",
        "advocate": "coordinator",
        "koncipient": "animator",
        "secretariat": "animator",
    }
    for old, new in old_to_new.items():
        db.session.execute(
            db.text("UPDATE users SET role = :new WHERE role = :old"),
            {"old": old, "new": new},
        )
    db.session.commit()

    try:
        role_columns = db.session.execute(db.text("PRAGMA table_info(managed_roles)")).fetchall()
    except Exception:
        role_columns = []

    if role_columns:
        role_existing = {str(column[1]).lower() for column in role_columns}
        if "rights" not in role_existing:
            db.session.execute(db.text("ALTER TABLE managed_roles ADD COLUMN rights JSON"))
            db.session.execute(db.text("UPDATE managed_roles SET rights = '{}' WHERE rights IS NULL"))
            db.session.commit()

    table_rows = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'"))
    table_names = {str(row[0]).lower() for row in table_rows}
    has_watchers = "watchers" in table_names
    has_legacy_project_watchers = "project_watchers" in table_names
    has_legacy_task_watchers = "task_watchers" in table_names

    if has_watchers or (not has_legacy_project_watchers and not has_legacy_task_watchers):
        return

    db.session.execute(db.text("PRAGMA foreign_keys=OFF"))
    db.session.execute(
        db.text(
            """
            CREATE TABLE IF NOT EXISTS watchers (
                id INTEGER NOT NULL,
                project_id INTEGER,
                task_id INTEGER,
                user_id INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT uq_project_watcher UNIQUE (project_id, user_id),
                CONSTRAINT uq_task_watcher UNIQUE (task_id, user_id),
                CONSTRAINT ck_watcher_target CHECK (
                    (project_id IS NOT NULL AND task_id IS NULL) OR
                    (project_id IS NULL AND task_id IS NOT NULL)
                ),
                FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
    )

    if has_legacy_project_watchers:
        db.session.execute(
            db.text(
                """
                INSERT OR IGNORE INTO watchers (project_id, task_id, user_id, created_at)
                SELECT project_id, NULL, user_id, created_at
                FROM project_watchers
                """
            )
        )
        db.session.execute(db.text("DROP TABLE project_watchers"))

    if has_legacy_task_watchers:
        db.session.execute(
            db.text(
                """
                INSERT OR IGNORE INTO watchers (project_id, task_id, user_id, created_at)
                SELECT NULL, task_id, user_id, created_at
                FROM task_watchers
                """
            )
        )
        db.session.execute(db.text("DROP TABLE task_watchers"))

    db.session.execute(db.text("PRAGMA foreign_keys=ON"))
    db.session.commit()


__all__ = [
    "User",
    "UserRole",
    "ManagedRole",
    "UserManagedRole",
    "ROLE_RIGHTS",
    "normalize_role_rights",
    "get_effective_role_rights",
    "user_has_right",
    "RoleLabelSetting",
    "Project",
    "ProjectStatus",
    "Sprint",
    "SprintStatus",
    "TaskBoardSetting",
    "TaskSavedFilter",
    "Notification",
    "ApiToken",
    "ProjectMembership",
    "ProjectMembershipRole",
    "Watcher",
    "AutomationRule",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskLabel",
    "TaskChecklistItem",
    "TaskActivity",
    "TaskAttachment",
    "Document",
    "DocumentType",
    "Comment",
    "ChatSession",
    "ChatMessage",
    "ChatMessageRole",
    "init_db",
]
