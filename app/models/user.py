import enum
from datetime import datetime

from flask_login import UserMixin

from ..extensions import db


class UserRole(enum.Enum):
    ADMIN = "admin"
    LEADER = "leader"
    COORDINATOR = "coordinator"
    SECRETARIAT = "secretariat"
    ANIMATOR = "animator"


ROLE_RIGHTS = {
    "view_all_projects",
    "manage_projects",
    "manage_roles",
}


SYSTEM_ROLE_RIGHTS = {
    "admin": {
        "view_all_projects": True,
        "manage_projects": True,
        "manage_roles": True,
    },
    "basic": {
        "view_all_projects": False,
        "manage_projects": False,
        "manage_roles": False,
    },
}


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
    watchers = db.relationship("Watcher", back_populates="user", cascade="all, delete-orphan")
    managed_role_assignment = db.relationship(
        "UserManagedRole",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )


class RoleLabelSetting(db.Model):
    __tablename__ = "role_label_settings"

    id = db.Column(db.Integer, primary_key=True)
    role_value = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(100), nullable=False)


class ManagedRole(db.Model):
    __tablename__ = "managed_roles"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    rights = db.Column(db.JSON, nullable=False, default=dict)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user_assignments = db.relationship("UserManagedRole", back_populates="role", cascade="all, delete-orphan")


class UserManagedRole(db.Model):
    __tablename__ = "user_managed_roles"
    __table_args__ = (
        db.UniqueConstraint("user_id", name="uq_user_managed_role_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("managed_roles.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="managed_role_assignment")
    role = db.relationship("ManagedRole", back_populates="user_assignments")


def assign_managed_role(user, managed_role):
    assignment = UserManagedRole.query.filter_by(user_id=user.id).first()
    if assignment is None:
        assignment = UserManagedRole(user_id=user.id, role_id=managed_role.id)
        db.session.add(assignment)
    else:
        assignment.role_id = managed_role.id

    user.role = UserRole.ADMIN if managed_role.key == "admin" else UserRole.ANIMATOR


def normalize_role_rights(rights):
    normalized = {}
    source = rights if isinstance(rights, dict) else {}
    for key in ROLE_RIGHTS:
        normalized[key] = bool(source.get(key, False))
    return normalized


def get_effective_role_rights(managed_role):
    if managed_role is None:
        return normalize_role_rights({})

    base = SYSTEM_ROLE_RIGHTS.get(managed_role.key, {})
    merged = normalize_role_rights(base)
    merged.update(normalize_role_rights(managed_role.rights or {}))

    if managed_role.key == "admin":
        return normalize_role_rights({key: True for key in ROLE_RIGHTS})
    return merged


def user_has_right(user, right):
    if right not in ROLE_RIGHTS:
        return False
    if user is None:
        return False

    assignment = user.managed_role_assignment
    if assignment is None or assignment.role is None:
        return user.role == UserRole.ADMIN
    return bool(get_effective_role_rights(assignment.role).get(right, False))


def ensure_default_managed_roles():
    admin_role = ManagedRole.query.filter_by(key="admin").first()
    basic_role = ManagedRole.query.filter_by(key="basic").first()

    changed = False
    if admin_role is None:
        admin_role = ManagedRole(key="admin", name="Admin", rights=SYSTEM_ROLE_RIGHTS["admin"], is_system=True)
        db.session.add(admin_role)
        changed = True
    elif admin_role.rights != SYSTEM_ROLE_RIGHTS["admin"]:
        admin_role.rights = SYSTEM_ROLE_RIGHTS["admin"]
        changed = True

    if basic_role is None:
        basic_role = ManagedRole(key="basic", name="Basic", rights=SYSTEM_ROLE_RIGHTS["basic"], is_system=True)
        db.session.add(basic_role)
        changed = True
    elif basic_role.rights != SYSTEM_ROLE_RIGHTS["basic"]:
        basic_role.rights = SYSTEM_ROLE_RIGHTS["basic"]
        changed = True

    if changed:
        db.session.flush()

    assigned_user_ids = {
        assignment.user_id
        for assignment in UserManagedRole.query.with_entities(UserManagedRole.user_id).all()
    }

    for user in User.query.all():
        if user.id in assigned_user_ids:
            continue
        role_id = admin_role.id if user.role == UserRole.ADMIN else basic_role.id
        db.session.add(UserManagedRole(user_id=user.id, role_id=role_id))
        if role_id != admin_role.id and user.role != UserRole.ANIMATOR:
            user.role = UserRole.ANIMATOR
            changed = True
        if role_id == admin_role.id and user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
            changed = True
        changed = True

    assignments = UserManagedRole.query.join(ManagedRole).join(User).all()
    for assignment in assignments:
        target_role = UserRole.ADMIN if assignment.role.key == "admin" else UserRole.ANIMATOR
        if assignment.user.role != target_role:
            assignment.user.role = target_role
            changed = True

    if changed:
        db.session.commit()
