import enum
import secrets
from datetime import datetime

from ..extensions import db


class SprintStatus(enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    CLOSED = "closed"


class ProjectMembershipRole(enum.Enum):
    VIEWER = "viewer"
    MEMBER = "member"
    MANAGER = "manager"
    ADMIN = "admin"


class Sprint(db.Model):
    __tablename__ = "sprints"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    goal = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.Enum(SprintStatus, name="sprint_status", native_enum=False),
        nullable=False,
        default=SprintStatus.PLANNED,
    )
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="sprints")
    creator = db.relationship("User", foreign_keys=[created_by])
    tasks = db.relationship("Task", back_populates="sprint")


class TaskBoardSetting(db.Model):
    __tablename__ = "task_board_settings"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    todo_label = db.Column(db.String(80), nullable=False, default="To Do")
    in_progress_label = db.Column(db.String(80), nullable=False, default="In Progress")
    in_review_label = db.Column(db.String(80), nullable=False, default="In Review")
    done_label = db.Column(db.String(80), nullable=False, default="Done")
    wip_todo = db.Column(db.Integer, nullable=True)
    wip_in_progress = db.Column(db.Integer, nullable=True)
    wip_in_review = db.Column(db.Integer, nullable=True)
    wip_done = db.Column(db.Integer, nullable=True)
    swimlane_mode = db.Column(db.String(30), nullable=False, default="none")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="board_setting")


class TaskSavedFilter(db.Model):
    __tablename__ = "task_saved_filters"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(30), nullable=True)
    assignee_id = db.Column(db.Integer, nullable=True)
    label = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="saved_task_filters")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel = db.Column(db.String(30), nullable=False, default="in_app")
    kind = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="notifications")


class ApiToken(db.Model):
    __tablename__ = "api_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(80), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="api_tokens")

    @staticmethod
    def generate_value():
        return secrets.token_urlsafe(32)


class ProjectMembership(db.Model):
    __tablename__ = "project_memberships"
    __table_args__ = (
        db.UniqueConstraint("project_id", "user_id", name="uq_project_membership"),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(
        db.Enum(ProjectMembershipRole, name="project_membership_role", native_enum=False),
        nullable=False,
        default=ProjectMembershipRole.MEMBER,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="memberships")
    user = db.relationship("User", back_populates="project_memberships")


class Watcher(db.Model):
    __tablename__ = "watchers"
    __table_args__ = (
        db.UniqueConstraint("project_id", "user_id", name="uq_project_watcher"),
        db.UniqueConstraint("task_id", "user_id", name="uq_task_watcher"),
        db.CheckConstraint(
            "(project_id IS NOT NULL AND task_id IS NULL) OR (project_id IS NULL AND task_id IS NOT NULL)",
            name="ck_watcher_target",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="watchers")
    task = db.relationship("Task", back_populates="watchers")
    user = db.relationship("User", back_populates="watchers")


class AutomationRule(db.Model):
    __tablename__ = "automation_rules"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    trigger_type = db.Column(db.String(40), nullable=False)
    condition_value = db.Column(db.String(120), nullable=True)
    action_type = db.Column(db.String(40), nullable=False)
    action_value = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="automation_rules")
