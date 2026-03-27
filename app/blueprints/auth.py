from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..cache_helpers import warm_cache_for_user
from ..extensions import db, login_manager
from ..models.user import User, UserRole


auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember_me = request.form.get("remember_me") == "on"

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember_me)
            warm_cache_for_user(user.id)
            flash("Successfully signed in.", "success")
            return redirect(url_for("dashboard.index", _prefetch="1"))

        flash("Invalid email or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role_value = request.form.get("role", UserRole.ANIMATOR.value).strip().lower()

        if not username or not email or not password:
            flash("Username, email, and password are required.", "error")
            return render_template("auth/register.html", role_values=[role.value for role in UserRole])

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html", role_values=[role.value for role in UserRole])

        if User.query.filter_by(email=email).first() is not None:
            flash("Email is already in use.", "error")
            return render_template("auth/register.html", role_values=[role.value for role in UserRole])

        if User.query.filter_by(username=username).first() is not None:
            flash("Username is already in use.", "error")
            return render_template("auth/register.html", role_values=[role.value for role in UserRole])

        try:
            role = UserRole(role_value)
        except ValueError:
            flash("Invalid role selected.", "error")
            return render_template("auth/register.html", role_values=[role.value for role in UserRole])

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        warm_cache_for_user(user.id)
        flash("Account created successfully.", "success")
        return redirect(url_for("dashboard.index", _prefetch="1"))

    return render_template("auth/register.html", role_values=[role.value for role in UserRole])


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
