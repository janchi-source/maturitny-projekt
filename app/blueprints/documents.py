from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from ..cache_helpers import get_projects_dropdown
from ..extensions import db
from ..models.document import Document, DocumentType
from ..models.project import Project
from ..services.document_service import process_upload


documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/")
@login_required
def index():
    project_filter = request.args.get("project", "").strip()
    file_type_filter = request.args.get("file_type", "").strip().lower()
    tag_filter = request.args.get("tag", "").strip().lower()
    search = request.args.get("search", "").strip()

    query = Document.query
    if project_filter.isdigit():
        query = query.filter(Document.project_id == int(project_filter))

    if file_type_filter:
        try:
            query = query.filter(Document.file_type == DocumentType(file_type_filter))
        except ValueError:
            pass

    if search:
        query = query.filter(Document.original_name.ilike(f"%{search}%"))

    documents = query.order_by(Document.created_at.desc()).all()
    if tag_filter:
        documents = [doc for doc in documents if any(tag_filter in (tag or "") for tag in (doc.tags or []))]

    return render_template(
        "documents/list.html",
        documents=documents,
        projects=get_projects_dropdown(),
        project_filter=project_filter,
        file_type_filter=file_type_filter,
        tag_filter=tag_filter,
        search=search,
        file_type_values=[value.value for value in DocumentType],
    )


@documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    projects = get_projects_dropdown()

    if request.method == "POST":
        file = request.files.get("file")
        project_id_raw = request.form.get("project_id", "").strip()
        tags_raw = request.form.get("tags", "")

        if file is None or not file.filename:
            flash("Please select a file to upload.", "error")
            return render_template("documents/upload.html", projects=projects)

        if not project_id_raw.isdigit():
            flash("Please select a valid project.", "error")
            return render_template("documents/upload.html", projects=projects)

        tags = [part.strip() for part in tags_raw.split(",") if part.strip()]
        try:
            document = process_upload(
                file=file,
                project_id=int(project_id_raw),
                user_id=current_user.id,
                tags=tags,
                upload_root=current_app.config.get("UPLOAD_FOLDER", "uploads"),
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("documents/upload.html", projects=projects)
        except Exception:
            flash("Upload failed. Please try again.", "error")
            return render_template("documents/upload.html", projects=projects)

        flash("Document uploaded successfully.", "success")
        return redirect(url_for("documents.detail", document_id=document.id))

    return render_template("documents/upload.html", projects=projects)


@documents_bp.route("/<int:document_id>")
@login_required
def detail(document_id):
    document = Document.query.get_or_404(document_id)
    return render_template("documents/detail.html", document=document)


@documents_bp.route("/<int:document_id>/download")
@login_required
def download(document_id):
    document = Document.query.get_or_404(document_id)
    upload_root = Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    return send_from_directory(upload_root, document.filename, as_attachment=True, download_name=document.original_name)


@documents_bp.route("/<int:document_id>/delete", methods=["POST"])
@login_required
def delete(document_id):
    document = Document.query.get_or_404(document_id)
    upload_root = Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    file_path = upload_root / document.filename
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

    db.session.delete(document)
    db.session.commit()
    flash("Document deleted.", "info")
    return redirect(url_for("documents.index"))
