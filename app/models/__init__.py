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
from .user import RoleLabelSetting, User, UserRole


def init_db():
    db.create_all()
    _ensure_legacy_schema_updates()


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


__all__ = [
    "User",
    "UserRole",
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
