import re

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload, subqueryload

from ..extensions import db
from ..models.user import (
    ROLE_RIGHTS,
    ManagedRole,
    User,
    UserManagedRole,
    UserRole,
    assign_managed_role,
    ensure_default_managed_roles,
    get_effective_role_rights,
    normalize_role_rights,
    user_has_right,
)


team_bp = Blueprint("team", __name__)

RIGHT_LABELS = {
    "view_all_projects": "View All Projects",
    "manage_projects": "Manage Projects",
    "manage_roles": "Manage Roles",
}


@team_bp.route("/")
@login_required
def index():
    ensure_default_managed_roles()
    users = (
        User.query.options(
            subqueryload(User.owned_projects),
            subqueryload(User.assigned_tasks),
            joinedload(User.managed_role_assignment).joinedload(UserManagedRole.role),
        )
        .order_by(User.username.asc())
        .all()
    )
    member_stats = []
    for user in users:
        assignment = user.managed_role_assignment
        role_key = assignment.role.key if assignment and assignment.role else ("admin" if user.role == UserRole.ADMIN else "basic")
        role_label = assignment.role.name if assignment and assignment.role else ("Admin" if user.role == UserRole.ADMIN else "Basic")
        member_stats.append(
            {
                "user": user,
                "project_count": len(user.owned_projects),
                "task_count": len(user.assigned_tasks),
                "role_key": role_key,
                "role_label": role_label,
            }
        )

    return render_template(
        "team/list.html",
        member_stats=member_stats,
        is_admin=user_has_right(current_user, "manage_roles"),
    )


@team_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit(user_id):
    _require_manage_roles_right()
    ensure_default_managed_roles()
    user = User.query.get_or_404(user_id)
    managed_roles = ManagedRole.query.order_by(ManagedRole.is_system.desc(), ManagedRole.name.asc()).all()
    selected_role_id = user.managed_role_assignment.role_id if user.managed_role_assignment else None

    if request.method == "POST":
        role_id_raw = request.form.get("role_id", "").strip()
        if not role_id_raw.isdigit():
            flash("Invalid role selected.", "error")
            return render_template(
                "team/form.html",
                user=user,
                managed_roles=managed_roles,
                selected_role_id=selected_role_id,
            )

        managed_role = ManagedRole.query.filter_by(id=int(role_id_raw)).first()
        if managed_role is None:
            flash("Invalid role selected.", "error")
            return render_template(
                "team/form.html",
                user=user,
                managed_roles=managed_roles,
                selected_role_id=selected_role_id,
            )

        if user.id == current_user.id and managed_role.key != "admin":
            flash("You cannot remove your own admin role.", "error")
            return render_template(
                "team/form.html",
                user=user,
                managed_roles=managed_roles,
                selected_role_id=selected_role_id,
            )

        assign_managed_role(user, managed_role)

        db.session.commit()
        flash("User role updated.", "success")
        return redirect(url_for("team.index"))

    return render_template(
        "team/form.html",
        user=user,
        managed_roles=managed_roles,
        selected_role_id=selected_role_id,
    )


@team_bp.route("/roles", methods=["GET", "POST"])
@login_required
def manage_roles():
    _require_manage_roles_right()
    ensure_default_managed_roles()
    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "create":
            role_name = request.form.get("role_name", "").strip()
            if not role_name:
                flash("Role name is required.", "error")
                return redirect(url_for("team.manage_roles"))

            role_key = re.sub(r"[^a-z0-9]+", "_", role_name.lower()).strip("_")
            if not role_key:
                flash("Role name must contain letters or numbers.", "error")
                return redirect(url_for("team.manage_roles"))

            if ManagedRole.query.filter_by(key=role_key).first() is not None:
                flash("Role already exists.", "error")
                return redirect(url_for("team.manage_roles"))

            db.session.add(ManagedRole(key=role_key, name=role_name, rights=normalize_role_rights({}), is_system=False))
            db.session.commit()
            flash("Role created.", "success")
            return redirect(url_for("team.manage_roles"))

        if action == "delete":
            role_id_raw = request.form.get("role_id", "").strip()
            if not role_id_raw.isdigit():
                flash("Invalid role selected.", "error")
                return redirect(url_for("team.manage_roles"))

            role = ManagedRole.query.filter_by(id=int(role_id_raw)).first()
            if role is None:
                flash("Role not found.", "error")
                return redirect(url_for("team.manage_roles"))

            if role.is_system or role.key in {"admin", "basic"}:
                flash("System roles cannot be deleted.", "error")
                return redirect(url_for("team.manage_roles"))

            basic_role = ManagedRole.query.filter_by(key="basic").first()
            if basic_role is None:
                flash("Basic role is missing.", "error")
                return redirect(url_for("team.manage_roles"))

            assignments = UserManagedRole.query.filter_by(role_id=role.id).all()
            for assignment in assignments:
                assignment.role_id = basic_role.id
                if assignment.user:
                    assignment.user.role = UserRole.ANIMATOR

            db.session.delete(role)
            db.session.commit()
            flash("Role deleted. Affected users were reassigned to Basic.", "success")
            return redirect(url_for("team.manage_roles"))

        flash("Unsupported role action.", "error")
        return redirect(url_for("team.manage_roles"))

    roles = ManagedRole.query.order_by(ManagedRole.is_system.desc(), ManagedRole.name.asc()).all()
    role_counts = {
        role_id: count
        for role_id, count in db.session.query(UserManagedRole.role_id, db.func.count(UserManagedRole.id)).group_by(UserManagedRole.role_id).all()
    }
    return render_template("team/roles.html", roles=roles, role_counts=role_counts, right_labels=RIGHT_LABELS)


@team_bp.route("/roles/<int:role_id>/rights", methods=["GET", "POST"])
@login_required
def edit_role_rights(role_id):
    _require_manage_roles_right()
    ensure_default_managed_roles()

    role = ManagedRole.query.get_or_404(role_id)
    rights_keys = sorted(ROLE_RIGHTS)
    rights_labels = {key: RIGHT_LABELS.get(key, key.replace("_", " ").title()) for key in rights_keys}

    if request.method == "POST":
        if role.key == "admin":
            flash("Admin role rights are fixed and cannot be changed.", "error")
            return redirect(url_for("team.edit_role_rights", role_id=role.id))

        updated_rights = {}
        for right_key in rights_keys:
            updated_rights[right_key] = request.form.get(f"right_{right_key}") == "on"

        role.rights = normalize_role_rights(updated_rights)
        db.session.commit()
        flash("Role rights updated.", "success")
        return redirect(url_for("team.manage_roles"))

    effective_rights = get_effective_role_rights(role)
    return render_template(
        "team/role_rights.html",
        role=role,
        rights_keys=rights_keys,
        rights_labels=rights_labels,
        effective_rights=effective_rights,
        is_admin_system_role=(role.key == "admin"),
    )


@team_bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
def delete(user_id):
    _require_manage_roles_right()
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot remove your own account.", "error")
        return redirect(url_for("team.index"))

    db.session.delete(user)
    db.session.commit()
    flash("User removed.", "info")
    return redirect(url_for("team.index"))


def _require_manage_roles_right():
    if not user_has_right(current_user, "manage_roles"):
        abort(403)
