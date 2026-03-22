from .extensions import cache
from .models.project import Project
from .models.task import TaskLabel
from .models.user import User


@cache.cached(timeout=120, key_prefix="all_projects_dropdown")
def get_projects_dropdown():
    return Project.query.order_by(Project.name.asc()).all()


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
