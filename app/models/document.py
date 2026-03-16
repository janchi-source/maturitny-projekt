import enum
from datetime import datetime

from ..extensions import db


class DocumentType(enum.Enum):
    PDF = "pdf"
    DOCX = "docx"


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(
        db.Enum(DocumentType, name="document_type", native_enum=False),
        nullable=False,
    )
    file_size = db.Column(db.Integer, nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    tags = db.Column(db.JSON, nullable=False, default=list)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    lock_version = db.Column(db.Integer, nullable=False, default=1)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="documents")
    uploader = db.relationship("User", back_populates="uploaded_documents", foreign_keys=[uploaded_by])
    updater = db.relationship("User", foreign_keys=[updated_by])
    chat_sessions = db.relationship("ChatSession", back_populates="document", cascade="all, delete-orphan")
    linked_tasks = db.relationship(
        "Task",
        secondary="task_document_links",
        back_populates="linked_documents",
        lazy="selectin",
    )
    revisions = db.relationship(
        "DocumentRevision",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentRevision.version.desc()",
    )


class DocumentRevision(db.Model):
    __tablename__ = "document_revisions"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)
    change_note = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    document = db.relationship("Document", back_populates="revisions")
    creator = db.relationship("User", foreign_keys=[created_by])
