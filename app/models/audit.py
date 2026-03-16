from datetime import datetime

from ..extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    resource_type = db.Column(db.String(80), nullable=False)
    resource_id = db.Column(db.String(80), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    actor = db.relationship("User", back_populates="audit_logs", foreign_keys=[actor_id])
