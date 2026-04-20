import os
from pathlib import Path

from flask import Flask, g, redirect, render_template, request
from flask_login import current_user
from sqlalchemy import event
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash

from config import Config

from .blueprints.ai_chat import ai_chat_bp
from .blueprints.auth import auth_bp
from .blueprints.dashboard import dashboard_bp
from .blueprints.documents import documents_bp
from .blueprints.projects import projects_bp
from .blueprints.settings import settings_bp
from .blueprints.tasks import tasks_bp
from .blueprints.team import team_bp
from .extensions import cache, csrf, db, login_manager
from .models import init_db

try:
    from .blueprints.workspaces import workspaces_bp
except ModuleNotFoundError as exc:
    if exc.name != "app.blueprints.workspaces":
        raise
    workspaces_bp = None


def create_app(config_class=Config):
    import re as _re

    if os.getenv("VERCEL"):
        app = Flask(__name__, instance_path="/tmp/instance")
    else:
        app = Flask(__name__)

    @app.template_filter("strip_mentions")
    def strip_mentions_filter(text):
        return _re.sub(r'@\[[a-z]+:\d+:([^\]]+)\]', r'@\1', text or "")
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=app.config.get("PROXY_FIX_X_FOR", 1),
        x_proto=app.config.get("PROXY_FIX_X_PROTO", 1),
        x_host=app.config.get("PROXY_FIX_X_HOST", 1),
        x_port=app.config.get("PROXY_FIX_X_PORT", 1),
        x_prefix=app.config.get("PROXY_FIX_X_PREFIX", 1),
    )

    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    if not upload_folder.is_absolute():
        upload_folder = Path(app.root_path).parent / upload_folder
    try:
        upload_folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback_upload_folder = Path("/tmp/uploads")
        fallback_upload_folder.mkdir(parents=True, exist_ok=True)
        upload_folder = fallback_upload_folder
    app.config["UPLOAD_FOLDER"] = str(upload_folder.resolve())

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    cache.init_app(app)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(projects_bp, url_prefix="/projects")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")
    app.register_blueprint(documents_bp, url_prefix="/documents")
    app.register_blueprint(ai_chat_bp, url_prefix="/ai-chat")
    app.register_blueprint(team_bp, url_prefix="/team")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    if workspaces_bp is not None:
        app.register_blueprint(workspaces_bp, url_prefix="/workspaces")

    @app.before_request
    def _enforce_https():
        if not app.config.get("ENFORCE_HTTPS", False):
            return None
        if request.is_secure or app.debug or app.testing:
            return None
        if request.method in ("OPTIONS",):
            return None
        if request.path.startswith("/.well-known/"):
            return None
        host = (request.host or "").split(":", 1)[0].lower()
        if host in {"localhost", "127.0.0.1", "::1"}:
            return None
        return redirect(request.url.replace("http://", "https://", 1), code=301)

    @app.after_request
    def _set_hsts_header(response):
        if not app.config.get("HSTS_ENABLED", False):
            return response
        if request.is_secure:
            max_age = int(app.config.get("HSTS_MAX_AGE", 31536000))
            value = f"max-age={max_age}"
            if app.config.get("HSTS_INCLUDE_SUBDOMAINS", True):
                value += "; includeSubDomains"
            if app.config.get("HSTS_PRELOAD", False):
                value += "; preload"
            response.headers["Strict-Transport-Security"] = value
        return response

    @app.context_processor
    def inject_workspace_context():
        if current_user.is_authenticated:
            try:
                from .models.workspace import WorkspaceMembership
            except ModuleNotFoundError as exc:
                if exc.name != "app.models.workspace":
                    raise
                return {"user_has_workspace": False}

            if not hasattr(g, "_has_workspace"):
                g._has_workspace = (
                    WorkspaceMembership.query.filter_by(user_id=current_user.id).first() is not None
                )
            return {"user_has_workspace": g._has_workspace}
        return {"user_has_workspace": False}

    @app.context_processor
    def inject_role_label_map():
        role_label_map = {
            "admin": "Admin",
            "animator": "Basic",
            "leader": "Basic",
            "coordinator": "Basic",
            "secretariat": "Basic",
        }
        return {"role_label_map": role_label_map}

    @app.context_processor
    def inject_header_notifications():
        if current_user.is_authenticated:
            from .models.planning import Notification
            unread = (
                Notification.query
                .filter_by(user_id=current_user.id, is_read=False, channel="in_app")
                .order_by(Notification.created_at.desc())
                .limit(5)
                .all()
            )
            return {"header_notifications": unread, "header_unread_count": len(unread)}
        return {"header_notifications": [], "header_unread_count": 0}

    register_error_handlers(app)

    @event.listens_for(db.session, "after_commit")
    def clear_cache_after_commit(session):
        cache.clear()

    with app.app_context():
        init_db()
        ensure_builtin_admin(app)

    return app


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500


def ensure_builtin_admin(app):
    from .models.user import ManagedRole, User, UserManagedRole, UserRole

    username = str(app.config.get("BUILTIN_ADMIN_USERNAME", "")).strip()
    email = str(app.config.get("BUILTIN_ADMIN_EMAIL", "")).strip().lower()
    password = str(app.config.get("BUILTIN_ADMIN_PASSWORD", "")).strip()

    if not username or not email or not password:
        return

    admin_role = ManagedRole.query.filter_by(key="admin").first()
    if admin_role is None:
        return

    user_by_email = User.query.filter_by(email=email).first()
    user_by_username = User.query.filter_by(username=username).first()
    user = user_by_email or user_by_username

    if user is None:
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=UserRole.ADMIN,
        )
        db.session.add(user)
        db.session.flush()
    else:
        if user.email != email and (user_by_email is None or user_by_email.id == user.id):
            user.email = email
        if user.username != username and (user_by_username is None or user_by_username.id == user.id):
            user.username = username

        user.password_hash = generate_password_hash(password)

    assignment = UserManagedRole.query.filter_by(user_id=user.id).first()
    if assignment is None:
        db.session.add(UserManagedRole(user_id=user.id, role_id=admin_role.id))
    else:
        assignment.role_id = admin_role.id

    if user.role != UserRole.ADMIN:
        user.role = UserRole.ADMIN

    db.session.commit()
