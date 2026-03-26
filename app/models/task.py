import enum
from datetime import datetime

from ..extensions import db


class TaskStatus(enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TaskPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


task_labels = db.Table(
    "task_labels",
    db.Column("task_id", db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    db.Column("label_id", db.Integer, db.ForeignKey("task_labels_master.id", ondelete="CASCADE"), primary_key=True),
)


task_dependencies = db.Table(
    "task_dependencies",
    db.Column("blocker_id", db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    db.Column("blocked_id", db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
)


class TaskLabel(db.Model):
    __tablename__ = "task_labels_master"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    color = db.Column(db.String(32), nullable=False, default="slate")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    tasks = db.relationship("Task", secondary=task_labels, back_populates="labels")


class TaskChecklistItem(db.Model):
    __tablename__ = "task_checklist_items"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship("Task", back_populates="checklist_items")


class TaskActivity(db.Model):
    __tablename__ = "task_activities"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship("Task", back_populates="activities")
    actor = db.relationship("User")


class AttachmentStatus(enum.Enum):
    ACTIVE = "active"
    PENDING = "pending"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class TaskAttachment(db.Model):
    __tablename__ = "task_attachments"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    version = db.Column(db.Integer, nullable=False, default=1)
    version_note = db.Column(db.Text, nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(
        db.Enum(AttachmentStatus, name="attachment_status", native_enum=False),
        nullable=False,
        default=AttachmentStatus.ACTIVE,
    )

    task = db.relationship("Task", back_populates="attachments")
    uploader = db.relationship("User", back_populates="task_attachments", foreign_keys=[uploaded_by])


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.Enum(TaskStatus, name="task_status", native_enum=False),
        nullable=False,
        default=TaskStatus.TODO,
    )
    priority = db.Column(
        db.Enum(TaskPriority, name="task_priority", native_enum=False),
        nullable=False,
        default=TaskPriority.MEDIUM,
    )
    progress = db.Column(db.Integer, nullable=False, default=0)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sprint_id = db.Column(db.Integer, db.ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="tasks")
    sprint = db.relationship("Sprint", back_populates="tasks")
    assignee = db.relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    comments = db.relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    labels = db.relationship("TaskLabel", secondary=task_labels, back_populates="tasks")
    checklist_items = db.relationship(
        "TaskChecklistItem",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskChecklistItem.created_at.asc()",
    )
    activities = db.relationship(
        "TaskActivity",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskActivity.created_at.desc()",
    )
    attachments = db.relationship(
        "TaskAttachment",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskAttachment.created_at.desc()",
    )
    blocked_tasks = db.relationship(
        "Task",
        secondary=task_dependencies,
        primaryjoin=id == task_dependencies.c.blocker_id,
        secondaryjoin=id == task_dependencies.c.blocked_id,
        backref="blocking_tasks",
    )
