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
    ProjectWatcher,
    Sprint,
    SprintStatus,
    TaskBoardSetting,
    TaskSavedFilter,
    TaskWatcher,
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

    # Migrate old role values to new role names
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
    "TaskWatcher",
    "ProjectWatcher",
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
