import csv
import io

from flask import Blueprint, Response, render_template, request

from ..blueprints import role_required
from ..models.audit import AuditLog
from ..models.planning import ProjectMembership
from ..models.project import Project
from ..models.task import Task
from ..models.user import User, UserRole


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@role_required(UserRole.ADMIN, UserRole.OWNER)
def dashboard():
    stats = {
        "users": User.query.count(),
        "projects": Project.query.count(),
        "tasks": Task.query.count(),
        "memberships": ProjectMembership.query.count(),
    }

    recent_audit = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(25).all()
    return render_template("admin/dashboard.html", stats=stats, recent_audit=recent_audit)


@admin_bp.route("/audit")
@role_required(UserRole.ADMIN, UserRole.OWNER)
def audit_log():
    action_filter = request.args.get("action", "").strip().lower()
    resource_filter = request.args.get("resource", "").strip().lower()

    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    if resource_filter:
        query = query.filter(AuditLog.resource_type.ilike(f"%{resource_filter}%"))

    entries = query.order_by(AuditLog.created_at.desc()).limit(300).all()
    return render_template(
        "admin/audit_log.html",
        entries=entries,
        action_filter=action_filter,
        resource_filter=resource_filter,
    )


@admin_bp.route("/reports/permissions.csv")
@role_required(UserRole.ADMIN, UserRole.OWNER)
def permissions_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["project_id", "project_name", "user_id", "username", "email", "role", "assigned_at"])

    memberships = (
        ProjectMembership.query.join(Project, ProjectMembership.project_id == Project.id)
        .join(User, ProjectMembership.user_id == User.id)
        .order_by(Project.id.asc(), User.username.asc())
        .all()
    )

    for membership in memberships:
        writer.writerow(
            [
                membership.project_id,
                membership.project.name if membership.project else "",
                membership.user_id,
                membership.user.username if membership.user else "",
                membership.user.email if membership.user else "",
                membership.role.value,
                membership.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )

    data = output.getvalue()
    output.close()
    return Response(data, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=permission_matrix.csv"})
