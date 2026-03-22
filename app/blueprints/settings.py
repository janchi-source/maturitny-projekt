from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models.user import User


settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "profile":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()

            if not username or not email:
                flash("Username and email are required.", "error")
                return render_template("settings/index.html")

            if username != current_user.username:
                if User.query.filter_by(username=username).first():
                    flash("Username is already taken.", "error")
                    return render_template("settings/index.html")

            if email != current_user.email:
                if User.query.filter_by(email=email).first():
                    flash("Email is already in use.", "error")
                    return render_template("settings/index.html")

            current_user.username = username
            current_user.email = email
            db.session.commit()
            flash("Profile updated successfully.", "success")

        elif action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not check_password_hash(current_user.password_hash, current_password):
                flash("Current password is incorrect.", "error")
                return render_template("settings/index.html")

            if len(new_password) < 8:
                flash("New password must be at least 8 characters.", "error")
                return render_template("settings/index.html")

            if new_password != confirm_password:
                flash("New passwords do not match.", "error")
                return render_template("settings/index.html")

            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash("Password changed successfully.", "success")

        return redirect(url_for("settings.index"))

    return render_template("settings/index.html")
