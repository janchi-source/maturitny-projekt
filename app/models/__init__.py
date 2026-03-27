from ..extensions import db
from .audit import AuditLog
from .ai_chat import ChatMessage, ChatMessageRole, ChatSession
from .comment import Comment
from .document import Document, DocumentRevision, DocumentType
from .planning import (
    ApiToken,
    AutomationRule,
    Notification,
    ProjectInvite,
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
from .task import (
    Task,
    TaskActivity,
    TaskAttachment,
    TaskAttachmentRevision,
    TaskChecklistItem,
    TaskDocumentLinkHistory,
    TaskLabel,
    TaskPriority,
    TaskStatus,
)
from .user import User, UserRole


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
    if "parent_task_id" not in existing:
        db.session.execute(db.text("ALTER TABLE tasks ADD COLUMN parent_task_id INTEGER"))
    if "story_points" not in existing:
        db.session.execute(db.text("ALTER TABLE tasks ADD COLUMN story_points INTEGER DEFAULT 0 NOT NULL"))

    try:
        document_columns = db.session.execute(db.text("PRAGMA table_info(documents)")).fetchall()
    except Exception:
        document_columns = []

    document_existing = {str(column[1]).lower() for column in document_columns}
    if document_columns and "updated_by" not in document_existing:
        db.session.execute(db.text("ALTER TABLE documents ADD COLUMN updated_by INTEGER"))
    if document_columns and "lock_version" not in document_existing:
        db.session.execute(db.text("ALTER TABLE documents ADD COLUMN lock_version INTEGER DEFAULT 1 NOT NULL"))
    if document_columns and "is_deleted" not in document_existing:
        db.session.execute(db.text("ALTER TABLE documents ADD COLUMN is_deleted BOOLEAN DEFAULT 0 NOT NULL"))
    if document_columns and "deleted_at" not in document_existing:
        db.session.execute(db.text("ALTER TABLE documents ADD COLUMN deleted_at DATETIME"))
    if document_columns and "updated_at" not in document_existing:
        db.session.execute(db.text("ALTER TABLE documents ADD COLUMN updated_at DATETIME"))

    try:
        attachment_columns = db.session.execute(db.text("PRAGMA table_info(task_attachments)")).fetchall()
    except Exception:
        attachment_columns = []

    attachment_existing = {str(column[1]).lower() for column in attachment_columns}
    if attachment_columns and "file_hash" not in attachment_existing:
        db.session.execute(db.text("ALTER TABLE task_attachments ADD COLUMN file_hash VARCHAR(64)"))
    if attachment_columns and "lock_version" not in attachment_existing:
        db.session.execute(db.text("ALTER TABLE task_attachments ADD COLUMN lock_version INTEGER DEFAULT 1 NOT NULL"))
    if attachment_columns and "is_deleted" not in attachment_existing:
        db.session.execute(db.text("ALTER TABLE task_attachments ADD COLUMN is_deleted BOOLEAN DEFAULT 0 NOT NULL"))
    if attachment_columns and "deleted_at" not in attachment_existing:
        db.session.execute(db.text("ALTER TABLE task_attachments ADD COLUMN deleted_at DATETIME"))

    try:
        filter_columns = db.session.execute(db.text("PRAGMA table_info(task_saved_filters)")).fetchall()
    except Exception:
        filter_columns = []

    filter_existing = {str(column[1]).lower() for column in filter_columns}
    if filter_columns and "hierarchy" not in filter_existing:
        db.session.execute(db.text("ALTER TABLE task_saved_filters ADD COLUMN hierarchy VARCHAR(30) DEFAULT 'all' NOT NULL"))

    try:
        invite_columns = db.session.execute(db.text("PRAGMA table_info(project_invites)")).fetchall()
    except Exception:
        invite_columns = []

    if not invite_columns:
        db.session.execute(
            db.text(
                """
                CREATE TABLE IF NOT EXISTS project_invites (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    code VARCHAR(32) NOT NULL UNIQUE,
                    role VARCHAR(20) NOT NULL,
                    created_by INTEGER,
                    created_at DATETIME NOT NULL,
                    expires_at DATETIME NOT NULL,
                    used_at DATETIME,
                    used_by INTEGER,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY(used_by) REFERENCES users(id) ON DELETE SET NULL
                )
                """
            )
        )

    db.session.commit()


__all__ = [
    "User",
    "UserRole",
    "Project",
    "ProjectStatus",
    "Sprint",
    "SprintStatus",
    "TaskBoardSetting",
    "TaskSavedFilter",
    "Notification",
    "ApiToken",
    "ProjectInvite",
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
    "TaskAttachmentRevision",
    "TaskDocumentLinkHistory",
    "Document",
    "DocumentRevision",
    "DocumentType",
    "Comment",
    "ChatSession",
    "ChatMessage",
    "ChatMessageRole",
    "AuditLog",
    "init_db",
]
