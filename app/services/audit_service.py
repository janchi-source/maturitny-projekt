from flask_login import current_user

from ..extensions import db
from ..models.audit import AuditLog


def log_audit(action, resource_type, resource_id=None, details=""):
    actor_id = current_user.id if current_user.is_authenticated else None
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details or None,
    )
    db.session.add(entry)
    return entry
