import enum
from datetime import datetime

from ..extensions import db


class ProjectStatus(enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.Enum(ProjectStatus, name="project_status", native_enum=False),
        nullable=False,
        default=ProjectStatus.ACTIVE,
    )
    progress = db.Column(db.Integer, nullable=False, default=0)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = db.relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    tasks = db.relationship("Task", back_populates="project", cascade="all, delete-orphan")
    documents = db.relationship("Document", back_populates="project", cascade="all, delete-orphan")
    sprints = db.relationship("Sprint", back_populates="project", cascade="all, delete-orphan")
    board_setting = db.relationship(
        "TaskBoardSetting",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    memberships = db.relationship("ProjectMembership", back_populates="project", cascade="all, delete-orphan")
    watchers = db.relationship("Watcher", back_populates="project", cascade="all, delete-orphan")
    automation_rules = db.relationship("AutomationRule", back_populates="project", cascade="all, delete-orphan")
