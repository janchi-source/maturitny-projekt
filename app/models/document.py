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
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="documents")
    uploader = db.relationship("User", back_populates="uploaded_documents", foreign_keys=[uploaded_by])
    chat_sessions = db.relationship("ChatSession", back_populates="document", cascade="all, delete-orphan")
