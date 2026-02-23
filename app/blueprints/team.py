from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..blueprints import role_required
from ..extensions import db
from ..models.user import User, UserRole


team_bp = Blueprint("team", __name__)


@team_bp.route("/")
@login_required
def index():
    users = User.query.order_by(User.username.asc()).all()
    member_stats = []
    for user in users:
        member_stats.append(
            {
                "user": user,
                "project_count": len(user.owned_projects),
                "task_count": len(user.assigned_tasks),
            }
        )

    return render_template(
        "team/list.html",
        member_stats=member_stats,
        is_admin=current_user.role == UserRole.ADMIN,
    )


@team_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@role_required(UserRole.ADMIN)
def edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        role_value = request.form.get("role", "").strip().lower()
        try:
            user.role = UserRole(role_value)
        except ValueError:
            flash("Invalid role selected.", "error")
            return render_template(
                "team/form.html",
                user=user,
                role_values=[role.value for role in UserRole],
            )

        db.session.commit()
        flash("User role updated.", "success")
        return redirect(url_for("team.index"))

    return render_template(
        "team/form.html",
        user=user,
        role_values=[role.value for role in UserRole],
    )


@team_bp.route("/<int:user_id>/delete", methods=["POST"])
@role_required(UserRole.ADMIN)
def delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot remove your own account.", "error")
        return redirect(url_for("team.index"))

    db.session.delete(user)
    db.session.commit()
    flash("User removed.", "info")
    return redirect(url_for("team.index"))
