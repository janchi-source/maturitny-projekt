from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload, subqueryload

from ..cache_helpers import get_users_dropdown
from ..extensions import db
from ..models.document import Document
from ..models.planning import AutomationRule, ProjectMembership, ProjectMembershipRole, ProjectWatcher
from ..models.project import Project, ProjectStatus
from ..models.task import Task, TaskPriority, TaskStatus
from ..models.user import User
from ..models.user import UserRole


projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip().lower()

    query = Project.query
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
    project = (
        Project.query.options(
            subqueryload(Project.tasks).joinedload(Task.assignee),
            subqueryload(Project.documents).joinedload(Document.uploader),
            subqueryload(Project.memberships).joinedload(ProjectMembership.user),
            subqueryload(Project.watchers).joinedload(ProjectWatcher.user),
            subqueryload(Project.automation_rules),
            joinedload(Project.owner),
        )
        .get_or_404(project_id)
    )
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

    return render_template(
        "projects/detail.html",
        project=project,
        active_tab=active_tab,
        tasks=sorted(project.tasks, key=lambda task: task.created_at, reverse=True),
        documents=sorted(project.documents, key=lambda document: document.created_at, reverse=True),
        team_members=team_members,
        users_for_membership=get_users_dropdown(),
        membership_map=membership_map,
        membership_roles=[role.value for role in ProjectMembershipRole],
        watchers=watchers,
        is_watching=is_watching,
        automation_rules=sorted(project.automation_rules, key=lambda rule: rule.created_at, reverse=True),
        can_manage=_can_manage_projects(),
        users=get_users_dropdown(),
        priority_values=[p.value for p in TaskPriority],
        status_values=[s.value for s in TaskStatus],
    )


@projects_bp.route("/<int:project_id>/watch", methods=["POST"])
@login_required
def toggle_watch(project_id):
    project = Project.query.get_or_404(project_id)
    watcher = ProjectWatcher.query.filter_by(project_id=project.id, user_id=current_user.id).first()

    if watcher:
        db.session.delete(watcher)
        flash("Stopped watching project.", "info")
    else:
        db.session.add(ProjectWatcher(project_id=project.id, user_id=current_user.id))
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
    else:
        membership.role = role

    db.session.commit()
    flash("Project membership updated.", "success")
    return redirect(url_for("projects.detail", project_id=project.id, tab="team"))


@projects_bp.route("/<int:project_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_member(project_id, user_id):
    project = Project.query.get_or_404(project_id)
    _require_project_manager()

    membership = ProjectMembership.query.filter_by(project_id=project.id, user_id=user_id).first()
    if membership:
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
