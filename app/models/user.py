import enum
from datetime import datetime

from flask_login import UserMixin

from ..extensions import db


class UserRole(enum.Enum):
    ADMIN = "admin"
    LEADER = "leader"
    COORDINATOR = "coordinator"
    ANIMATOR = "animator"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.ANIMATOR,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    owned_projects = db.relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="Project.owner_id",
    )
    assigned_tasks = db.relationship(
        "Task",
        back_populates="assignee",
        foreign_keys="Task.assignee_id",
    )
    uploaded_documents = db.relationship(
        "Document",
        back_populates="uploader",
        foreign_keys="Document.uploaded_by",
    )
    comments = db.relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    task_attachments = db.relationship(
        "TaskAttachment",
        back_populates="uploader",
        foreign_keys="TaskAttachment.uploaded_by",
    )
    chat_sessions = db.relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    saved_task_filters = db.relationship("TaskSavedFilter", back_populates="user", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    api_tokens = db.relationship("ApiToken", back_populates="user", cascade="all, delete-orphan")
    project_memberships = db.relationship("ProjectMembership", back_populates="user", cascade="all, delete-orphan")
    task_watchers = db.relationship("TaskWatcher", back_populates="user", cascade="all, delete-orphan")
    project_watchers = db.relationship("ProjectWatcher", back_populates="user", cascade="all, delete-orphan")


class RoleLabelSetting(db.Model):
    __tablename__ = "role_label_settings"

    id = db.Column(db.Integer, primary_key=True)
    role_value = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(100), nullable=False)
