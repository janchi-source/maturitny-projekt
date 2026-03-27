from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models.planning import (
    AutomationRule,
    ProjectInvite,
    ProjectMembership,
    ProjectMembershipRole,
    ProjectWatcher,
)
from ..models.project import Project, ProjectStatus
from ..models.user import User
from ..models.user import UserRole
from ..services.audit_service import log_audit


projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip().lower()

    query = _accessible_projects_query(ProjectMembershipRole.VIEWER)
    if search:
        query = query.filter(Project.name.ilike(f"%{search}%"))

    if status_filter:
        try:
            query = query.filter(Project.status == ProjectStatus(status_filter))
        except ValueError:
            pass

    projects = query.order_by(Project.updated_at.desc()).all()
    return render_template(
        "projects/list.html",
        projects=projects,
        search=search,
        status_filter=status_filter,
        status_values=[status.value for status in ProjectStatus],
        can_manage=_can_manage_projects(),
    )


@projects_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    _require_project_manager()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        status_value = request.form.get("status", ProjectStatus.ACTIVE.value).strip().lower()

        if not name:
            flash("Project name is required.", "error")
            return render_template(
                "projects/form.html",
                form_mode="create",
                project=None,
                status_values=[status.value for status in ProjectStatus],
            )

        try:
            status = ProjectStatus(status_value)
        except ValueError:
            flash("Invalid project status.", "error")
            return render_template(
                "projects/form.html",
                form_mode="create",
                project=None,
                status_values=[status.value for status in ProjectStatus],
            )

        project = Project(
            name=name,
            description=description,
            status=status,
            progress=0,
            owner_id=current_user.id,
        )
        db.session.add(project)
        db.session.commit()
        log_audit(
            action="project.created",
            resource_type="project",
            resource_id=project.id,
            details=f"Project created: {project.name}",
        )
        db.session.commit()

        flash("Project created successfully.", "success")
        return redirect(url_for("projects.detail", project_id=project.id))

    return render_template(
        "projects/form.html",
        form_mode="create",
        project=None,
        status_values=[status.value for status in ProjectStatus],
    )


@projects_bp.route("/<int:project_id>")
@login_required
def detail(project_id):
    project = Project.query.get_or_404(project_id)
    _require_project_role(project.id, ProjectMembershipRole.VIEWER)
    active_tab = request.args.get("tab", "tasks").strip().lower()
    if active_tab not in {"tasks", "documents", "team"}:
        active_tab = "tasks"

    team_map = {}
    if project.owner:
        team_map[project.owner.id] = project.owner

    for task in project.tasks:
        if task.assignee:
            team_map[task.assignee.id] = task.assignee

    for document in project.documents:
        if document.uploader:
            team_map[document.uploader.id] = document.uploader

    for membership in project.memberships:
        if membership.user:
            team_map[membership.user.id] = membership.user

    team_members = list(team_map.values())
    membership_map = {membership.user_id: membership for membership in project.memberships}
    is_watching = ProjectWatcher.query.filter_by(project_id=project.id, user_id=current_user.id).first() is not None
    watchers = [watch.user for watch in project.watchers if watch.user]
    active_invites = sorted(
        [invite for invite in project.invites if invite.is_available()],
        key=lambda invite: invite.created_at,
        reverse=True,
    )

    return render_template(
        "projects/detail.html",
        project=project,
        active_tab=active_tab,
        tasks=sorted(project.tasks, key=lambda task: task.created_at, reverse=True),
        documents=sorted(project.documents, key=lambda document: document.created_at, reverse=True),
        team_members=team_members,
        users_for_membership=User.query.order_by(User.username.asc()).all(),
        membership_map=membership_map,
        membership_roles=[role.value for role in ProjectMembershipRole],
        active_invites=active_invites,
        watchers=watchers,
        is_watching=is_watching,
        automation_rules=sorted(project.automation_rules, key=lambda rule: rule.created_at, reverse=True),
        can_manage=_can_manage_projects(),
    )


@projects_bp.route("/<int:project_id>/watch", methods=["POST"])
@login_required
def toggle_watch(project_id):
    project = Project.query.get_or_404(project_id)
    _require_project_role(project.id, ProjectMembershipRole.VIEWER)
    watcher = ProjectWatcher.query.filter_by(project_id=project.id, user_id=current_user.id).first()

    if watcher:
        db.session.delete(watcher)
        log_audit(
            action="project.watch_removed",
            resource_type="project",
            resource_id=project.id,
            details=f"Watcher removed: user #{current_user.id}",
        )
        flash("Stopped watching project.", "info")
    else:
        db.session.add(ProjectWatcher(project_id=project.id, user_id=current_user.id))
        log_audit(
            action="project.watch_added",
            resource_type="project",
            resource_id=project.id,
            details=f"Watcher added: user #{current_user.id}",
        )
        flash("Now watching project.", "success")

    db.session.commit()
    return redirect(url_for("projects.detail", project_id=project.id, tab="team"))


@projects_bp.route("/<int:project_id>/members", methods=["POST"])
@login_required
def upsert_member(project_id):
    project = Project.query.get_or_404(project_id)
    _require_project_manager()

    user_id_raw = request.form.get("user_id", "").strip()
    role_raw = request.form.get("role", "").strip().lower()

    if not user_id_raw.isdigit():
        flash("User is required.", "error")
        return redirect(url_for("projects.detail", project_id=project.id, tab="team"))

    try:
        role = ProjectMembershipRole(role_raw)
    except ValueError:
        flash("Invalid membership role.", "error")
        return redirect(url_for("projects.detail", project_id=project.id, tab="team"))

    membership = ProjectMembership.query.filter_by(project_id=project.id, user_id=int(user_id_raw)).first()
    if not membership:
        membership = ProjectMembership(project_id=project.id, user_id=int(user_id_raw), role=role)
        db.session.add(membership)
        audit_message = f"Membership created for user #{user_id_raw} as {role.value}"
    else:
        previous_role = membership.role.value
        membership.role = role
        audit_message = f"Membership role updated for user #{user_id_raw}: {previous_role} -> {role.value}"

    log_audit(
        action="project.membership_upsert",
        resource_type="project",
        resource_id=project.id,
        details=audit_message,
    )

    db.session.commit()
    flash("Project membership updated.", "success")
    return redirect(url_for("projects.detail", project_id=project.id, tab="team"))


@projects_bp.route("/<int:project_id>/invites", methods=["POST"])
@login_required
def create_invite(project_id):
    project = Project.query.get_or_404(project_id)
    _require_project_manager()

    role_raw = request.form.get("role", "").strip().lower()
    try:
        role = ProjectMembershipRole(role_raw)
    except ValueError:
        flash("Invalid invite role.", "error")
        return redirect(url_for("projects.detail", project_id=project.id, tab="team"))

    code = ProjectInvite.generate_code()
    while ProjectInvite.query.filter_by(code=code).first():
        code = ProjectInvite.generate_code()

    invite = ProjectInvite(
        project_id=project.id,
        code=code,
        role=role,
        created_by=current_user.id,
        expires_at=ProjectInvite.default_expiry(),
    )
    db.session.add(invite)
    log_audit(
        action="project.invite_created",
        resource_type="project",
        resource_id=project.id,
        details=f"Invite code created with role {role.value}",
    )
    db.session.commit()
    flash("Invite code generated (expires in 24 hours).", "success")
    return redirect(url_for("projects.detail", project_id=project.id, tab="team"))


@projects_bp.route("/join", methods=["POST"])
@login_required
def join_with_invite():
    code = request.form.get("invite_code", "").strip()
    if not code:
        flash("Invite code is required.", "error")
        return redirect(url_for("projects.index"))

    invite = ProjectInvite.query.filter_by(code=code).first()
    if not invite:
        flash("Invite code is invalid.", "error")
        return redirect(url_for("projects.index"))

    if not invite.is_available():
        flash("Invite code is no longer available.", "error")
        return redirect(url_for("projects.index"))

    membership = ProjectMembership.query.filter_by(project_id=invite.project_id, user_id=current_user.id).first()
    if membership:
        membership.role = invite.role
    else:
        membership = ProjectMembership(
            project_id=invite.project_id,
            user_id=current_user.id,
            role=invite.role,
        )
        db.session.add(membership)

    invite.used_at = datetime.utcnow()
    invite.used_by = current_user.id

    log_audit(
        action="project.invite_redeemed",
        resource_type="project",
        resource_id=invite.project_id,
        details=f"Invite redeemed by user #{current_user.id} with role {invite.role.value}",
    )
    db.session.commit()
    flash("You joined the project successfully.", "success")
    return redirect(url_for("projects.detail", project_id=invite.project_id, tab="team"))


@projects_bp.route("/<int:project_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_member(project_id, user_id):
    project = Project.query.get_or_404(project_id)
    _require_project_manager()

    membership = ProjectMembership.query.filter_by(project_id=project.id, user_id=user_id).first()
    if membership:
        log_audit(
            action="project.membership_removed",
            resource_type="project",
            resource_id=project.id,
            details=f"Removed member user #{user_id}",
        )
        db.session.delete(membership)
        db.session.commit()
        flash("Project member removed.", "info")
    else:
        flash("Membership not found.", "error")

    return redirect(url_for("projects.detail", project_id=project.id, tab="team"))


@projects_bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        status_value = request.form.get("status", project.status.value).strip().lower()

        if not name:
            flash("Project name is required.", "error")
            return render_template(
                "projects/form.html",
                form_mode="edit",
                project=project,
                status_values=[status.value for status in ProjectStatus],
            )

        try:
            status = ProjectStatus(status_value)
        except ValueError:
            flash("Invalid project status.", "error")
            return render_template(
                "projects/form.html",
                form_mode="edit",
                project=project,
                status_values=[status.value for status in ProjectStatus],
            )

        project.name = name
        project.description = description
        project.status = status
        log_audit(
            action="project.updated",
            resource_type="project",
            resource_id=project.id,
            details=f"Updated project fields; status={project.status.value}",
        )
        db.session.commit()

        flash("Project updated successfully.", "success")
        return redirect(url_for("projects.detail", project_id=project.id))

    return render_template(
        "projects/form.html",
        form_mode="edit",
        project=project,
        status_values=[status.value for status in ProjectStatus],
    )


@projects_bp.route("/<int:project_id>/delete", methods=["POST"])
@login_required
def delete(project_id):
    _require_project_manager()
    project = Project.query.get_or_404(project_id)

    log_audit(
        action="project.deleted",
        resource_type="project",
        resource_id=project.id,
        details=f"Deleted project: {project.name}",
    )
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "info")
    return redirect(url_for("projects.index"))


def _can_manage_projects():
    if not current_user.is_authenticated:
        return False
    return current_user.role in {UserRole.ADMIN, UserRole.OWNER}


def _require_project_manager():
    if not _can_manage_projects():
        abort(403)


def _accessible_projects_query(required_role):
    if current_user.role.value in {"admin", "owner"}:
        return Project.query

    role_rank = {
        ProjectMembershipRole.VIEWER: 1,
        ProjectMembershipRole.MEMBER: 2,
        ProjectMembershipRole.MANAGER: 3,
        ProjectMembershipRole.ADMIN: 4,
    }

    memberships = ProjectMembership.query.filter_by(user_id=current_user.id).all()
    eligible_ids = [
        membership.project_id
        for membership in memberships
        if role_rank[membership.role] >= role_rank[required_role]
    ]

    if eligible_ids:
        return Project.query.filter(Project.id.in_(eligible_ids))

    no_membership_ids = [
        project_id
        for project_id, member_count in db.session.query(
            Project.id,
            func.count(ProjectMembership.id),
        )
        .outerjoin(ProjectMembership, ProjectMembership.project_id == Project.id)
        .group_by(Project.id)
        .all()
        if member_count == 0
    ]
    if no_membership_ids:
        return Project.query.filter(Project.id.in_(no_membership_ids))

    return Project.query.filter(Project.id == -1)


def _user_has_project_role(project_id, required_role):
    if current_user.role.value in {"admin", "owner"}:
        return True

    membership = ProjectMembership.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    has_memberships = ProjectMembership.query.filter_by(project_id=project_id).count() > 0
    if not has_memberships:
        return True
    if not membership:
        return False

    role_rank = {
        ProjectMembershipRole.VIEWER: 1,
        ProjectMembershipRole.MEMBER: 2,
        ProjectMembershipRole.MANAGER: 3,
        ProjectMembershipRole.ADMIN: 4,
    }
    return role_rank[membership.role] >= role_rank[required_role]


def _require_project_role(project_id, required_role):
    if not _user_has_project_role(project_id, required_role):
        abort(403)
