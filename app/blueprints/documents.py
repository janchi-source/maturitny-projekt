from pathlib import Path

from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models.document import Document, DocumentRevision, DocumentType
from ..models.planning import ProjectMembership, ProjectMembershipRole
from ..models.project import Project
from ..services.audit_service import log_audit
from ..services.document_service import process_upload


documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/")
@login_required
def index():
    project_filter = request.args.get("project", "").strip()
    file_type_filter = request.args.get("file_type", "").strip().lower()
    tag_filter = request.args.get("tag", "").strip().lower()
    search = request.args.get("search", "").strip()

    project_query = _accessible_projects_query(ProjectMembershipRole.VIEWER)

    query = Document.query.join(Project, Document.project_id == Project.id)
    query = query.filter(Project.id.in_(project_query.with_entities(Project.id)))
    query = query.filter(Document.is_deleted.is_(False))

    if project_filter.isdigit():
        requested_project_id = int(project_filter)
        if not _user_has_project_role(requested_project_id, ProjectMembershipRole.VIEWER):
            flash("You are not allowed to view documents for that project.", "error")
            return redirect(url_for("documents.index"))
        query = query.filter(Document.project_id == requested_project_id)

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
        projects=project_query.order_by(Project.name.asc()).all(),
        project_filter=project_filter,
        file_type_filter=file_type_filter,
        tag_filter=tag_filter,
        search=search,
        file_type_values=[value.value for value in DocumentType],
    )


@documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    projects = _accessible_projects_query(ProjectMembershipRole.MEMBER).order_by(Project.name.asc()).all()

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

        project_id = int(project_id_raw)
        _require_project_role(project_id, ProjectMembershipRole.MEMBER)

        tags = [part.strip() for part in tags_raw.split(",") if part.strip()]
        try:
            document = process_upload(
                file=file,
                project_id=project_id,
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

        log_audit(
            action="document.uploaded",
            resource_type="document",
            resource_id=document.id,
            details=f"Uploaded {document.original_name} to project #{document.project_id}",
        )
        db.session.commit()

        flash("Document uploaded successfully.", "success")
        return redirect(url_for("documents.detail", document_id=document.id))

    return render_template("documents/upload.html", projects=projects)


@documents_bp.route("/archived")
@login_required
def archived():
    project_filter = request.args.get("project", "").strip()

    project_query = _accessible_projects_query(ProjectMembershipRole.VIEWER)
    query = Document.query.join(Project, Document.project_id == Project.id)
    query = query.filter(Project.id.in_(project_query.with_entities(Project.id)))
    query = query.filter(Document.is_deleted.is_(True))

    if project_filter.isdigit():
        requested_project_id = int(project_filter)
        if not _user_has_project_role(requested_project_id, ProjectMembershipRole.VIEWER):
            flash("You are not allowed to view archived documents for that project.", "error")
            return redirect(url_for("documents.archived"))
        query = query.filter(Document.project_id == requested_project_id)

    archived_documents = query.order_by(Document.deleted_at.desc()).all()
    return render_template(
        "documents/archived.html",
        documents=archived_documents,
        projects=project_query.order_by(Project.name.asc()).all(),
        project_filter=project_filter,
    )


@documents_bp.route("/<int:document_id>")
@login_required
def detail(document_id):
    document = Document.query.filter_by(id=document_id, is_deleted=False).first_or_404()
    _require_project_role(document.project_id, ProjectMembershipRole.VIEWER)
    log_audit(
        action="document.viewed",
        resource_type="document",
        resource_id=document.id,
        details=f"Viewed document in project #{document.project_id}",
    )
    db.session.commit()
    revisions = DocumentRevision.query.filter_by(document_id=document.id).order_by(DocumentRevision.version.desc()).all()
    return render_template("documents/detail.html", document=document, revisions=revisions)


@documents_bp.route("/<int:document_id>/download")
@login_required
def download(document_id):
    document = Document.query.filter_by(id=document_id, is_deleted=False).first_or_404()
    _require_project_role(document.project_id, ProjectMembershipRole.VIEWER)
    log_audit(
        action="document.downloaded",
        resource_type="document",
        resource_id=document.id,
        details=f"Downloaded document from project #{document.project_id}",
    )
    db.session.commit()
    upload_root = Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    return send_from_directory(upload_root, document.filename, as_attachment=True, download_name=document.original_name)


@documents_bp.route("/<int:document_id>/revisions")
@login_required
def revisions(document_id):
    document = Document.query.filter_by(id=document_id, is_deleted=False).first_or_404()
    _require_project_role(document.project_id, ProjectMembershipRole.VIEWER)

    rows = DocumentRevision.query.filter_by(document_id=document.id).order_by(DocumentRevision.version.desc()).all()
    return render_template("documents/revisions.html", document=document, revisions=rows)


@documents_bp.route("/<int:document_id>/revisions/<int:revision_id>/download")
@login_required
def download_revision(document_id, revision_id):
    document = Document.query.filter_by(id=document_id, is_deleted=False).first_or_404()
    _require_project_role(document.project_id, ProjectMembershipRole.VIEWER)

    revision = DocumentRevision.query.filter_by(id=revision_id, document_id=document.id).first_or_404()
    upload_root = Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    return send_from_directory(upload_root, revision.filename, as_attachment=True, download_name=document.original_name)


@documents_bp.route("/<int:document_id>/delete", methods=["POST"])
@login_required
def delete(document_id):
    document = Document.query.filter_by(id=document_id, is_deleted=False).first_or_404()
    _require_project_role(document.project_id, ProjectMembershipRole.MANAGER)

    expected_lock_version_raw = request.form.get("lock_version", "").strip()
    expected_lock_version = int(expected_lock_version_raw) if expected_lock_version_raw.isdigit() else None
    if expected_lock_version is not None and document.lock_version != expected_lock_version:
        flash("Document changed since you loaded the page. Refresh and try again.", "error")
        return redirect(url_for("documents.detail", document_id=document.id))

    document.is_deleted = True
    document.deleted_at = datetime.utcnow()
    document.lock_version += 1
    document.updated_by = current_user.id

    log_audit(
        action="document.deleted",
        resource_type="document",
        resource_id=document.id,
        details=f"Deleted document {document.original_name} from project #{document.project_id}",
    )
    db.session.commit()
    flash("Document archived.", "info")
    return redirect(url_for("documents.index"))


@documents_bp.route("/<int:document_id>/restore", methods=["POST"])
@login_required
def restore(document_id):
    document = Document.query.filter_by(id=document_id, is_deleted=True).first_or_404()
    _require_project_role(document.project_id, ProjectMembershipRole.MANAGER)

    expected_lock_version_raw = request.form.get("lock_version", "").strip()
    expected_lock_version = int(expected_lock_version_raw) if expected_lock_version_raw.isdigit() else None
    if expected_lock_version is not None and document.lock_version != expected_lock_version:
        flash("Document changed since you loaded the page. Refresh and try again.", "error")
        return redirect(url_for("documents.archived"))

    document.is_deleted = False
    document.deleted_at = None
    document.lock_version += 1
    document.updated_by = current_user.id

    log_audit(
        action="document.restored",
        resource_type="document",
        resource_id=document.id,
        details=f"Restored document {document.original_name} in project #{document.project_id}",
    )
    db.session.commit()

    flash("Document restored.", "success")
    return redirect(url_for("documents.archived"))


def _accessible_projects_query(required_role):
    if current_user.role.value in {"admin", "owner"}:
        return Project.query

    role_rank = {
        ProjectMembershipRole.VIEWER: 1,
        ProjectMembershipRole.MEMBER: 2,
        ProjectMembershipRole.MANAGER: 3,
        ProjectMembershipRole.ADMIN: 4,
    }

    memberships = ProjectMembership.query.filter_by(user_id=current_user.id).all()
    eligible_ids = [
        membership.project_id
        for membership in memberships
        if role_rank[membership.role] >= role_rank[required_role]
    ]

    if eligible_ids:
        return Project.query.filter(Project.id.in_(eligible_ids))

    # Legacy fallback for projects that have no membership entries yet.
    no_membership_ids = [
        project_id
        for project_id, member_count in db.session.query(
            Project.id,
            func.count(ProjectMembership.id),
        )
        .outerjoin(ProjectMembership, ProjectMembership.project_id == Project.id)
        .group_by(Project.id)
        .all()
        if member_count == 0
    ]
    if no_membership_ids:
        return Project.query.filter(Project.id.in_(no_membership_ids))

    return Project.query.filter(Project.id == -1)


def _user_has_project_role(project_id, required_role):
    if current_user.role.value in {"admin", "owner"}:
        return True

    membership = ProjectMembership.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    has_memberships = ProjectMembership.query.filter_by(project_id=project_id).count() > 0
    if not has_memberships:
        return True
    if not membership:
        return False

    role_rank = {
        ProjectMembershipRole.VIEWER: 1,
        ProjectMembershipRole.MEMBER: 2,
        ProjectMembershipRole.MANAGER: 3,
        ProjectMembershipRole.ADMIN: 4,
    }
    return role_rank[membership.role] >= role_rank[required_role]


def _require_project_role(project_id, required_role):
    if not _user_has_project_role(project_id, required_role):
        abort(403)
