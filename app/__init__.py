from pathlib import Path

from flask import Flask, render_template
from flask_login import current_user
from sqlalchemy import event

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


def create_app(config_class=Config):
    import re as _re

    app = Flask(__name__)

    @app.template_filter("strip_mentions")
    def strip_mentions_filter(text):
        return _re.sub(r'@\[[a-z]+:\d+:([^\]]+)\]', r'@\1', text or "")
    app.config.from_object(config_class)

    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    if not upload_folder.is_absolute():
        upload_folder = Path(app.root_path).parent / upload_folder
    upload_folder.mkdir(parents=True, exist_ok=True)
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

    return app


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500
