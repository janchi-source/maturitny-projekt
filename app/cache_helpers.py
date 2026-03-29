from flask_login import current_user
from sqlalchemy import or_

from .extensions import cache, db
from .models.planning import ProjectMembership
from .models.project import Project
from .models.task import TaskLabel
from .models.user import User
from .models.user import user_has_right


def get_projects_dropdown():
    query = Project.query
    if current_user.is_authenticated and not user_has_right(current_user, "view_all_projects"):
        membership_project_ids = db.session.query(ProjectMembership.project_id).filter_by(user_id=current_user.id)
        query = query.filter(
            or_(
                Project.owner_id == current_user.id,
                Project.id.in_(membership_project_ids),
            )
        )
    return query.order_by(Project.name.asc()).all()


@cache.cached(timeout=120, key_prefix="all_users_dropdown")
def get_users_dropdown():
    return User.query.order_by(User.username.asc()).all()


@cache.cached(timeout=120, key_prefix="all_labels_dropdown")
def get_labels_dropdown():
    return TaskLabel.query.order_by(TaskLabel.name.asc()).all()


def warm_cache_for_user(user_id):
    """Pre-populate cached dropdown data after login."""
    get_projects_dropdown()
    get_users_dropdown()
    get_labels_dropdown()
