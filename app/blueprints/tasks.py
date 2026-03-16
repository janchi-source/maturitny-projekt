import csv
import hashlib
import io
import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models.comment import Comment
from ..models.document import Document, DocumentRevision
from ..models.planning import (
    ApiToken,
    AutomationRule,
    Notification,
    ProjectMembership,
    ProjectMembershipRole,
    Sprint,
    SprintStatus,
    TaskBoardSetting,
    TaskSavedFilter,
    TaskWatcher,
)
from ..models.project import Project
from ..models.task import (
    Task,
    TaskActivity,
    TaskAttachment,
    TaskAttachmentRevision,
    TaskChecklistItem,
    TaskDocumentLinkHistory,
    TaskLabel,
    TaskPriority,
    TaskStatus,
)
from ..models.user import User


tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/")
@login_required
def index():
    project_filter = request.args.get("project", "").strip()
    status_filter = request.args.get("status", "").strip().lower()
    assignee_filter = request.args.get("assignee", "").strip()
    label_filter = request.args.get("label", "").strip().lower()
    hierarchy_filter = request.args.get("hierarchy", "all").strip().lower()
    quick = request.args.get("quick", "").strip().lower()

    query = Task.query.options(
        joinedload(Task.assignee),
        joinedload(Task.labels),
        joinedload(Task.sprint),
        joinedload(Task.subtasks),
    )

    if project_filter.isdigit():
        query = query.filter(Task.project_id == int(project_filter))

    if status_filter:
        try:
            query = query.filter(Task.status == TaskStatus(status_filter))
        except ValueError:
            pass

    if assignee_filter.isdigit():
        query = query.filter(Task.assignee_id == int(assignee_filter))

    if label_filter:
        query = query.join(Task.labels).filter(func.lower(TaskLabel.name) == label_filter)

    if hierarchy_filter == "parents":
        query = query.filter(Task.parent_task_id.is_(None), Task.subtasks.any())
    elif hierarchy_filter == "subtasks":
        query = query.filter(Task.parent_task_id.isnot(None))
    elif hierarchy_filter == "top_level":
        query = query.filter(Task.parent_task_id.is_(None))
    else:
        hierarchy_filter = "all"

    now = datetime.now(UTC).replace(tzinfo=None)
    if quick == "my_tasks":
        query = query.filter(Task.assignee_id == current_user.id)
    elif quick == "overdue":
        query = query.filter(Task.due_date.isnot(None), Task.due_date < now, Task.status != TaskStatus.DONE)
    elif quick == "due_week":
        query = query.filter(Task.due_date.isnot(None), Task.due_date <= now + timedelta(days=7), Task.status != TaskStatus.DONE)
    elif quick == "high_priority":
        query = query.filter(Task.priority.in_([TaskPriority.HIGH, TaskPriority.CRITICAL]))

    tasks = query.order_by(Task.created_at.desc()).all()

    return render_template(
        "tasks/list.html",
        tasks=tasks,
        projects=Project.query.order_by(Project.name.asc()).all(),
        users=User.query.order_by(User.username.asc()).all(),
        labels=TaskLabel.query.order_by(TaskLabel.name.asc()).all(),
        saved_filters=TaskSavedFilter.query.filter_by(user_id=current_user.id).order_by(TaskSavedFilter.created_at.desc()).all(),
        project_filter=project_filter,
        status_filter=status_filter,
        assignee_filter=assignee_filter,
        label_filter=label_filter,
        hierarchy_filter=hierarchy_filter,
        quick=quick,
        status_values=[status.value for status in TaskStatus],
    )


@tasks_bp.route("/kanban")
@login_required
def kanban():
    project_filter = request.args.get("project", "").strip()
    swimlane_mode = request.args.get("swimlane", "").strip().lower()

    query = Task.query.options(
        joinedload(Task.assignee),
        joinedload(Task.labels),
        joinedload(Task.project),
        joinedload(Task.subtasks),
    )
    active_project = None
    setting = None

    if project_filter.isdigit():
        active_project = Project.query.get(int(project_filter))
        if active_project:
            query = query.filter(Task.project_id == active_project.id)
            setting = TaskBoardSetting.query.filter_by(project_id=active_project.id).first()

    tasks = query.order_by(Task.created_at.desc()).all()

    if setting and not swimlane_mode:
        swimlane_mode = setting.swimlane_mode
    if swimlane_mode not in {"none", "assignee", "project"}:
        swimlane_mode = "none"

    board_labels = {
        "todo": setting.todo_label if setting else "To Do",
        "in_progress": setting.in_progress_label if setting else "In Progress",
        "in_review": setting.in_review_label if setting else "In Review",
        "done": setting.done_label if setting else "Done",
    }
    wip_limits = {
        "todo": setting.wip_todo if setting else None,
        "in_progress": setting.wip_in_progress if setting else None,
        "in_review": setting.wip_in_review if setting else None,
        "done": setting.wip_done if setting else None,
    }

    if swimlane_mode == "none":
        columns = {
            TaskStatus.TODO: [],
            TaskStatus.IN_PROGRESS: [],
            TaskStatus.IN_REVIEW: [],
            TaskStatus.DONE: [],
        }
        for task in tasks:
            columns.setdefault(task.status, []).append(task)
        lane_columns = None
    else:
        lane_columns = defaultdict(
            lambda: {
                TaskStatus.TODO: [],
                TaskStatus.IN_PROGRESS: [],
                TaskStatus.IN_REVIEW: [],
                TaskStatus.DONE: [],
            }
        )
        for task in tasks:
            if swimlane_mode == "assignee":
                lane_key = task.assignee.username if task.assignee else "Unassigned"
            else:
                lane_key = task.project.name if task.project else "No Project"
            lane_columns[lane_key][task.status].append(task)
        columns = None

    return render_template(
        "tasks/kanban.html",
        columns=columns,
        lane_columns=dict(lane_columns) if lane_columns is not None else None,
        board_labels=board_labels,
        wip_limits=wip_limits,
        swimlane_mode=swimlane_mode,
        active_project=active_project,
        projects=Project.query.order_by(Project.name.asc()).all(),
        TaskStatus=TaskStatus,
        users=User.query.order_by(User.username.asc()).all(),
        priority_values=[priority.value for priority in TaskPriority],
        status_values=[status.value for status in TaskStatus],
    )


@tasks_bp.route("/kanban/settings", methods=["POST"])
@login_required
def update_kanban_settings():
    project_id = request.form.get("project_id", "").strip()
    if not project_id.isdigit():
        flash("Select a project to configure board settings.", "error")
        return redirect(url_for("tasks.kanban"))

    project = Project.query.get_or_404(int(project_id))
    _require_project_role(project.id, ProjectMembershipRole.MANAGER)

    setting = TaskBoardSetting.query.filter_by(project_id=project.id).first()
    if not setting:
        setting = TaskBoardSetting(project_id=project.id)
        db.session.add(setting)

    setting.todo_label = request.form.get("todo_label", "To Do").strip() or "To Do"
    setting.in_progress_label = request.form.get("in_progress_label", "In Progress").strip() or "In Progress"
    setting.in_review_label = request.form.get("in_review_label", "In Review").strip() or "In Review"
    setting.done_label = request.form.get("done_label", "Done").strip() or "Done"
    setting.swimlane_mode = request.form.get("swimlane_mode", "none").strip().lower()
    if setting.swimlane_mode not in {"none", "assignee", "project"}:
        setting.swimlane_mode = "none"

    setting.wip_todo = _safe_int_nullable(request.form.get("wip_todo"))
    setting.wip_in_progress = _safe_int_nullable(request.form.get("wip_in_progress"))
    setting.wip_in_review = _safe_int_nullable(request.form.get("wip_in_review"))
    setting.wip_done = _safe_int_nullable(request.form.get("wip_done"))

    db.session.commit()
    flash("Board settings updated.", "success")
    return redirect(url_for("tasks.kanban", project=project.id, swimlane=setting.swimlane_mode))


@tasks_bp.route("/filters/save", methods=["POST"])
@login_required
def save_filter():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Filter name is required.", "error")
        return redirect(url_for("tasks.index"))

    saved = TaskSavedFilter(
        user_id=current_user.id,
        name=name,
        project_id=int(request.form.get("project")) if (request.form.get("project", "").isdigit()) else None,
        status=request.form.get("status", "").strip() or None,
        assignee_id=int(request.form.get("assignee")) if (request.form.get("assignee", "").isdigit()) else None,
        label=request.form.get("label", "").strip() or None,
        hierarchy=request.form.get("hierarchy", "all").strip().lower() or "all",
    )

    if saved.hierarchy not in {"all", "parents", "top_level", "subtasks"}:
        saved.hierarchy = "all"

    db.session.add(saved)
    db.session.commit()
    flash("Filter saved.", "success")
    return redirect(url_for("tasks.index"))


@tasks_bp.route("/filters/<int:filter_id>/delete", methods=["POST"])
@login_required
def delete_filter(filter_id):
    saved = TaskSavedFilter.query.filter_by(id=filter_id, user_id=current_user.id).first_or_404()
    db.session.delete(saved)
    db.session.commit()
    flash("Saved filter deleted.", "info")
    return redirect(url_for("tasks.index"))


@tasks_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    projects = Project.query.order_by(Project.name.asc()).all()
    users = User.query.order_by(User.username.asc()).all()
    all_labels = TaskLabel.query.order_by(TaskLabel.name.asc()).all()
    selected_project_id = request.form.get("project_id", "").strip() if request.method == "POST" else ""
    parent_candidates = _parent_candidates(int(selected_project_id), exclude_task_id=None) if selected_project_id.isdigit() else []

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        project_id = request.form.get("project_id", "").strip()
        assignee_id = request.form.get("assignee_id", "").strip()
        priority_value = request.form.get("priority", TaskPriority.MEDIUM.value).strip().lower()
        status_value = request.form.get("status", TaskStatus.TODO.value).strip().lower()
        due_date_raw = request.form.get("due_date", "").strip()
        progress_raw = request.form.get("progress", "0").strip()
        story_points_raw = request.form.get("story_points", "0").strip()
        labels_raw = request.form.get("labels", "").strip()
        parent_task_id_raw = request.form.get("parent_task_id", "").strip()

        if not title or not project_id.isdigit():
            flash("Task title and project are required.", "error")
            return render_template(
                "tasks/form.html",
                form_mode="create",
                task=None,
                projects=projects,
                users=users,
                labels=all_labels,
                parent_candidates=parent_candidates,
                priority_values=[priority.value for priority in TaskPriority],
                status_values=[status.value for status in TaskStatus],
            )

        _require_project_role(int(project_id), ProjectMembershipRole.MEMBER)

        try:
            priority = TaskPriority(priority_value)
            status = TaskStatus(status_value)
        except ValueError:
            flash("Invalid task priority or status.", "error")
            return render_template(
                "tasks/form.html",
                form_mode="create",
                task=None,
                projects=projects,
                users=users,
                labels=all_labels,
                parent_candidates=parent_candidates,
                priority_values=[priority.value for priority in TaskPriority],
                status_values=[status.value for status in TaskStatus],
            )

        due_date = _parse_due_date_or_none(due_date_raw)
        if due_date_raw and due_date is None:
            flash("Invalid due date format.", "error")
            return render_template(
                "tasks/form.html",
                form_mode="create",
                task=None,
                projects=projects,
                users=users,
                labels=all_labels,
                parent_candidates=parent_candidates,
                priority_values=[priority.value for priority in TaskPriority],
                status_values=[status.value for status in TaskStatus],
            )

        parent_task_id = _parse_parent_task_id(parent_task_id_raw)
        if parent_task_id_raw and parent_task_id is None:
            flash("Invalid parent task selection.", "error")
            return render_template(
                "tasks/form.html",
                form_mode="create",
                task=None,
                projects=projects,
                users=users,
                parent_candidates=parent_candidates,
                priority_values=[priority.value for priority in TaskPriority],
                status_values=[status.value for status in TaskStatus],
            )

        parent_task = None
        if parent_task_id is not None:
            parent_task = Task.query.get_or_404(parent_task_id)
            if parent_task.project_id != int(project_id):
                flash("Parent task must belong to the same project.", "error")
                return render_template(
                    "tasks/form.html",
                    form_mode="create",
                    task=None,
                    projects=projects,
                    users=users,
                    labels=all_labels,
                    parent_candidates=parent_candidates,
                    priority_values=[priority.value for priority in TaskPriority],
                    status_values=[status.value for status in TaskStatus],
                )

        task = Task(
            title=title,
            description=description,
            status=status,
            priority=priority,
            story_points=_safe_story_points(story_points_raw),
            progress=_safe_progress(progress_raw),
            project_id=int(project_id),
            parent_task_id=parent_task_id,
            assignee_id=int(assignee_id) if assignee_id.isdigit() else None,
            due_date=due_date,
        )
        db.session.add(task)
        db.session.flush()

        _set_task_labels(task, labels_raw)
        _log_activity(task, "task_created", "Task created")
        _notify_assignment_if_needed(task, previous_assignee_id=None)
        _notify_due_date_if_needed(task, previous_due_date=None)
        _sync_parent_rollups(task=task)

        db.session.commit()
        flash("Task created successfully.", "success")
        if parent_task is not None:
            return redirect(url_for("tasks.detail", task_id=parent_task.id))
        return redirect(url_for("tasks.detail", task_id=task.id))

    return render_template(
        "tasks/form.html",
        form_mode="create",
        task=None,
        projects=projects,
        users=users,
        labels=all_labels,
        parent_candidates=parent_candidates,
        priority_values=[priority.value for priority in TaskPriority],
        status_values=[status.value for status in TaskStatus],
    )


@tasks_bp.route("/<int:task_id>")
@login_required
def detail(task_id):
    task = (
        Task.query.options(
            joinedload(Task.project),
            joinedload(Task.assignee),
            joinedload(Task.sprint),
            joinedload(Task.labels),
            joinedload(Task.comments).joinedload(Comment.author),
            joinedload(Task.checklist_items),
            joinedload(Task.activities).joinedload(TaskActivity.actor),
            joinedload(Task.attachments).joinedload(TaskAttachment.uploader),
            joinedload(Task.blocking_tasks),
            joinedload(Task.blocked_tasks),
            joinedload(Task.linked_documents),
            joinedload(Task.watchers).joinedload(TaskWatcher.user),
            joinedload(Task.subtasks).joinedload(Task.assignee),
            joinedload(Task.subtasks).joinedload(Task.labels),
            joinedload(Task.parent_task),
        )
        .filter(Task.id == task_id)
        .first_or_404()
    )

    _require_project_role(task.project_id, ProjectMembershipRole.VIEWER)

    available_dependencies = (
        Task.query.filter(Task.id != task.id, Task.project_id == task.project_id)
        .order_by(Task.title.asc())
        .all()
    )

    linked_document_ids = [document.id for document in task.linked_documents]
    available_documents_query = Document.query.filter(Document.project_id == task.project_id, Document.is_deleted.is_(False))
    if linked_document_ids:
        available_documents_query = available_documents_query.filter(~Document.id.in_(linked_document_ids))
    available_documents = available_documents_query.order_by(Document.created_at.desc()).all()

    completion_total = len(task.checklist_items)
    completion_done = sum(1 for item in task.checklist_items if item.is_done)

    current_watching = TaskWatcher.query.filter_by(task_id=task.id, user_id=current_user.id).first() is not None

    return render_template(
        "tasks/detail.html",
        task=task,
        projects=Project.query.order_by(Project.name.asc()).all(),
        users=User.query.order_by(User.username.asc()).all(),
        labels=TaskLabel.query.order_by(TaskLabel.name.asc()).all(),
        available_documents=available_documents,
        available_dependencies=available_dependencies,
        sprints=Sprint.query.filter_by(project_id=task.project_id).order_by(Sprint.created_at.desc()).all(),
        priority_values=[priority.value for priority in TaskPriority],
        status_values=[status.value for status in TaskStatus],
        parent_candidates=_parent_candidates(task.project_id, exclude_task_id=task.id),
        dependency_mermaid=_build_dependency_mermaid(task.project_id, task.id),
        checklist_done=completion_done,
        checklist_total=completion_total,
        is_watching=current_watching,
    )


@tasks_bp.route("/<int:task_id>/documents/link", methods=["POST"])
@login_required
def link_document(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    document_ref_raw = request.form.get("document_id", "").strip()
    document_id, expected_lock_version = _parse_document_ref(document_ref_raw)
    if document_id is None:
        flash("Select a valid document.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    document = Document.query.get_or_404(document_id)
    if document.project_id != task.project_id or document.is_deleted:
        flash("Document must belong to the same project.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if expected_lock_version is not None and document.lock_version != expected_lock_version:
        flash("Document changed since you loaded the page. Refresh and try again.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if document in task.linked_documents:
        flash("Document is already linked to this task.", "info")
        return redirect(url_for("tasks.detail", task_id=task.id))

    task.linked_documents.append(document)
    latest_revision = (
        DocumentRevision.query.filter_by(document_id=document.id)
        .order_by(DocumentRevision.version.desc())
        .first()
    )
    db.session.add(
        TaskDocumentLinkHistory(
            task_id=task.id,
            document_id=document.id,
            document_revision_id=latest_revision.id if latest_revision else None,
            linked_by=current_user.id,
            reason="Linked from task detail",
        )
    )
    document.lock_version += 1
    document.updated_by = current_user.id
    _log_activity(task, "document_linked", f"Linked document: {document.original_name}")
    db.session.commit()

    flash("Document linked to task.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/documents/<int:document_id>/unlink", methods=["POST"])
@login_required
def unlink_document(task_id, document_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    document = Document.query.get_or_404(document_id)
    expected_lock_version_raw = request.form.get("lock_version", "").strip()
    expected_lock_version = int(expected_lock_version_raw) if expected_lock_version_raw.isdigit() else None

    if expected_lock_version is not None and document.lock_version != expected_lock_version:
        flash("Document changed since you loaded the page. Refresh and try again.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if document in task.linked_documents:
        task.linked_documents.remove(document)
        link_record = (
            TaskDocumentLinkHistory.query.filter_by(
                task_id=task.id,
                document_id=document.id,
                unlinked_at=None,
            )
            .order_by(TaskDocumentLinkHistory.linked_at.desc())
            .first()
        )
        if link_record:
            link_record.unlinked_at = datetime.utcnow()
        document.lock_version += 1
        document.updated_by = current_user.id
        _log_activity(task, "document_unlinked", f"Unlinked document: {document.original_name}")
        db.session.commit()
        flash("Document unlinked from task.", "info")
    else:
        flash("Document link not found.", "error")

    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/watch", methods=["POST"])
@login_required
def toggle_watch(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.VIEWER)

    watcher = TaskWatcher.query.filter_by(task_id=task.id, user_id=current_user.id).first()
    if watcher:
        db.session.delete(watcher)
        flash("Stopped watching task.", "info")
    else:
        db.session.add(TaskWatcher(task_id=task.id, user_id=current_user.id))
        flash("Now watching task.", "success")

    db.session.commit()
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    projects = Project.query.order_by(Project.name.asc()).all()
    users = User.query.order_by(User.username.asc()).all()
    all_labels = TaskLabel.query.order_by(TaskLabel.name.asc()).all()

    if request.method == "POST":
        updates = {
            "title": request.form.get("title"),
            "description": request.form.get("description"),
            "project_id": request.form.get("project_id"),
            "assignee_id": request.form.get("assignee_id"),
            "priority": request.form.get("priority"),
            "status": request.form.get("status"),
            "due_date": request.form.get("due_date"),
            "story_points": request.form.get("story_points"),
            "progress": request.form.get("progress"),
            "labels": request.form.get("labels"),
            "parent_task_id": request.form.get("parent_task_id"),
        }

        try:
            changed_fields, previous = _apply_task_updates(task, updates, allow_partial=False)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "tasks/form.html",
                form_mode="edit",
                task=task,
                projects=projects,
                users=users,
                labels=all_labels,
                parent_candidates=_parent_candidates(task.project_id, exclude_task_id=task.id),
                priority_values=[priority.value for priority in TaskPriority],
                status_values=[status.value for status in TaskStatus],
            )

        if changed_fields:
            _log_activity(task, "task_updated", f"Updated: {', '.join(changed_fields)}")
            _run_automation_rules(task, changed_fields)
            _notify_assignment_if_needed(task, previous.get("assignee_id"))
            _notify_due_date_if_needed(task, previous.get("due_date"))
            _sync_parent_rollups(task=task, previous_parent_id=previous.get("parent_task_id"))

        db.session.commit()
        flash("Task updated successfully.", "success")
        return redirect(url_for("tasks.detail", task_id=task.id))

    return render_template(
        "tasks/form.html",
        form_mode="edit",
        task=task,
        projects=projects,
        users=users,
        labels=all_labels,
        parent_candidates=_parent_candidates(task.project_id, exclude_task_id=task.id),
        priority_values=[priority.value for priority in TaskPriority],
        status_values=[status.value for status in TaskStatus],
    )


@tasks_bp.route("/<int:task_id>/quick-update", methods=["POST"])
@login_required
def quick_update(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    payload = request.get_json(silent=True) if request.is_json else request.form
    payload = payload or {}

    try:
        changed_fields, previous = _apply_task_updates(task, payload, allow_partial=True)
    except ValueError as exc:
        if request.is_json:
            return jsonify({"success": False, "error": str(exc)}), 400
        flash(str(exc), "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    parent_updates = []
    if changed_fields:
        _log_activity(task, "task_updated", f"Updated: {', '.join(changed_fields)}")
        _run_automation_rules(task, changed_fields)
        _notify_assignment_if_needed(task, previous.get("assignee_id"))
        _notify_due_date_if_needed(task, previous.get("due_date"))
        parent_updates = _sync_parent_rollups(task=task, previous_parent_id=previous.get("parent_task_id"))
        db.session.commit()

    if request.is_json:
        return jsonify(
            {
                "success": True,
                "task_id": task.id,
                "status": task.status.value,
                "progress": task.progress,
                "changed": changed_fields,
                "parent_updates": parent_updates,
            }
        )

    flash("Task details updated.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/bulk", methods=["POST"])
@login_required
def bulk_action():
    task_ids = [int(task_id) for task_id in request.form.getlist("task_ids") if task_id.isdigit()]
    action = request.form.get("action", "").strip()

    if not task_ids:
        flash("Select at least one task.", "error")
        return redirect(url_for("tasks.index"))

    tasks = Task.query.filter(Task.id.in_(task_ids)).all()
    if not tasks:
        flash("No matching tasks found.", "error")
        return redirect(url_for("tasks.index"))

    for task in tasks:
        if action == "delete":
            _require_project_role(task.project_id, ProjectMembershipRole.MANAGER)
        else:
            _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    parent_ids_to_sync = set()

    try:
        if action == "assign":
            assignee_id_raw = request.form.get("bulk_assignee_id", "").strip()
            assignee_id = int(assignee_id_raw) if assignee_id_raw.isdigit() else None
            for task in tasks:
                previous = task.assignee_id
                task.assignee_id = assignee_id
                _notify_assignment_if_needed(task, previous)
                _log_activity(task, "bulk_assigned", "Bulk assign action")
        elif action == "status":
            status_raw = request.form.get("bulk_status", "").strip().lower()
            try:
                status_value = TaskStatus(status_raw)
            except ValueError:
                flash("Invalid bulk status.", "error")
                return redirect(url_for("tasks.index"))
            for task in tasks:
                if _has_unfinished_transition_requirements(task, status_value):
                    continue
                task.status = status_value
                _log_activity(task, "bulk_status_changed", f"Bulk status set to {status_value.value}")
                if task.parent_task_id:
                    parent_ids_to_sync.add(task.parent_task_id)
        elif action == "label":
            label_raw = request.form.get("bulk_label", "").strip()
            for task in tasks:
                combined = ",".join([label.name for label in task.labels] + ([label_raw] if label_raw else []))
                _set_task_labels(task, combined)
                _log_activity(task, "bulk_label_updated", "Bulk label action")
        elif action == "delete":
            selected_ids = {task.id for task in tasks}
            parent_with_remaining_children = [
                task
                for task in tasks
                if task.subtasks and any(subtask.id not in selected_ids for subtask in task.subtasks)
            ]
            if parent_with_remaining_children:
                parent_names = ", ".join(f"#{task.id}" for task in parent_with_remaining_children[:5])
                flash(
                    f"Cannot bulk delete parent tasks with remaining subtasks ({parent_names}). Select subtasks too or re-parent them first.",
                    "error",
                )
                return redirect(url_for("tasks.index"))
            parent_ids_to_sync.update(
                task.parent_task_id
                for task in tasks
                if task.parent_task_id and task.parent_task_id not in selected_ids
            )
            for task in tasks:
                db.session.delete(task)
            db.session.flush()
        else:
            flash("Unsupported bulk action.", "error")
            return redirect(url_for("tasks.index"))

        if parent_ids_to_sync:
            _sync_parent_rollups(parent_ids=parent_ids_to_sync)

        db.session.commit()
    except HTTPException:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        flash("Bulk action failed and was rolled back.", "error")
        return redirect(url_for("tasks.index"))

    flash("Bulk action executed.", "success")
    return redirect(url_for("tasks.index"))


@tasks_bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MANAGER)

    if task.subtasks:
        flash("Cannot delete a parent task while subtasks exist. Re-parent or delete subtasks first.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    parent_id = task.parent_task_id
    db.session.delete(task)
    db.session.flush()
    if parent_id:
        _sync_parent_rollups(parent_ids={parent_id})
    db.session.commit()
    flash("Task deleted.", "info")
    return redirect(url_for("tasks.index"))


@tasks_bp.route("/<int:task_id>/status", methods=["POST"])
@login_required
def update_status(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        status_value = str(payload.get("status", "")).strip().lower()
    else:
        status_value = request.form.get("status", "").strip().lower()

    try:
        requested_status = TaskStatus(status_value)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid status"}), 400

    blockers = _unfinished_blockers(task)
    unfinished_subtasks = _unfinished_subtasks(task)
    if blockers and requested_status in {TaskStatus.IN_REVIEW, TaskStatus.DONE}:
        return jsonify(
            {
                "success": False,
                "error": "Cannot move task while blockers are unfinished.",
                "blockers": [blocker.title for blocker in blockers],
            }
        ), 409
    if unfinished_subtasks and requested_status in {TaskStatus.IN_REVIEW, TaskStatus.DONE}:
        return jsonify(
            {
                "success": False,
                "error": "Cannot move parent task while subtasks are unfinished.",
                "subtasks": [subtask.title for subtask in unfinished_subtasks],
            }
        ), 409

    previous_status = task.status
    task.status = requested_status
    _log_activity(task, "status_changed", f"Status changed to {requested_status.value}")
    _run_automation_rules(task, ["status"])
    parent_updates = _sync_parent_rollups(task=task)

    if previous_status != requested_status:
        _notify_watchers(task, "Task status changed", f"{task.title} moved to {requested_status.value}.")

    db.session.commit()
    return jsonify(
        {
            "success": True,
            "task_id": task.id,
            "status": task.status.value,
            "parent_updates": parent_updates,
        }
    )


@tasks_bp.route("/<int:task_id>/labels", methods=["POST"])
@login_required
def update_labels(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)
    labels_raw = request.form.get("labels", "")
    changed = _set_task_labels(task, labels_raw)

    if changed:
        _log_activity(task, "labels_updated", "Labels updated")
        db.session.commit()
        flash("Labels updated.", "success")
    else:
        flash("No label changes detected.", "info")

    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/checklist", methods=["POST"])
@login_required
def add_checklist_item(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    title = request.form.get("title", "").strip()
    if not title:
        flash("Checklist item title is required.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    item = TaskChecklistItem(task_id=task.id, title=title)
    db.session.add(item)
    _log_activity(task, "checklist_item_added", f"Added checklist item: {title}")
    db.session.commit()
    flash("Checklist item added.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/checklist/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_checklist_item(task_id, item_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    item = TaskChecklistItem.query.filter_by(id=item_id, task_id=task.id).first_or_404()
    title = request.form.get("title", "").strip()
    if not title:
        flash("Checklist item title is required.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if item.title != title:
        original_title = item.title
        item.title = title
        _log_activity(task, "checklist_item_edited", f"Checklist item renamed: {original_title} -> {title}")
        db.session.commit()
        flash("Checklist item updated.", "success")
    else:
        flash("No checklist item changes detected.", "info")

    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/subtasks", methods=["POST"])
@login_required
def create_subtask(task_id):
    parent_task = Task.query.get_or_404(task_id)
    _require_project_role(parent_task.project_id, ProjectMembershipRole.MEMBER)

    title = request.form.get("title", "").strip()
    if not title:
        flash("Subtask title is required.", "error")
        return redirect(url_for("tasks.detail", task_id=parent_task.id))

    subtask = Task(
        title=title,
        description=request.form.get("description", "").strip(),
        project_id=parent_task.project_id,
        parent_task_id=parent_task.id,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        progress=0,
        assignee_id=None,
        due_date=None,
    )
    db.session.add(subtask)
    db.session.flush()

    _log_activity(parent_task, "subtask_created", f"Subtask created: #{subtask.id} {subtask.title}")
    _log_activity(subtask, "task_created", f"Subtask created under: #{parent_task.id} {parent_task.title}")
    _sync_parent_rollups(task=subtask)
    db.session.commit()

    flash("Subtask created.", "success")
    return redirect(url_for("tasks.detail", task_id=parent_task.id))


@tasks_bp.route("/<int:task_id>/checklist/<int:item_id>/toggle", methods=["POST"])
@login_required
def toggle_checklist_item(task_id, item_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    item = TaskChecklistItem.query.filter_by(id=item_id, task_id=task.id).first_or_404()
    item.is_done = not item.is_done
    state = "completed" if item.is_done else "reopened"
    _log_activity(task, "checklist_item_toggled", f"Checklist item {state}: {item.title}")
    db.session.commit()
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/checklist/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_checklist_item(task_id, item_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    item = TaskChecklistItem.query.filter_by(id=item_id, task_id=task.id).first_or_404()
    deleted_title = item.title
    db.session.delete(item)
    _log_activity(task, "checklist_item_deleted", f"Deleted checklist item: {deleted_title}")
    db.session.commit()
    flash("Checklist item removed.", "info")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/dependencies", methods=["POST"])
@login_required
def add_dependency(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    blocker_id = request.form.get("blocker_id", "").strip()

    if not blocker_id.isdigit():
        flash("Select a valid dependency task.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    blocker = Task.query.get_or_404(int(blocker_id))
    if blocker.id == task.id:
        flash("Task cannot depend on itself.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if blocker in task.blocking_tasks:
        flash("Dependency already exists.", "info")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if _creates_dependency_cycle(blocker, task):
        flash("Dependency would create a cycle.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    blocker.blocked_tasks.append(task)
    _log_activity(task, "dependency_added", f"Blocked by task: {blocker.title}")
    db.session.commit()
    flash("Dependency added.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/dependencies/<int:blocker_id>/remove", methods=["POST"])
@login_required
def remove_dependency(task_id, blocker_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    blocker = Task.query.get_or_404(blocker_id)

    if task in blocker.blocked_tasks:
        blocker.blocked_tasks.remove(task)
        _log_activity(task, "dependency_removed", f"Dependency removed: {blocker.title}")
        db.session.commit()
        flash("Dependency removed.", "success")
    else:
        flash("Dependency not found.", "info")

    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/attachments", methods=["POST"])
@login_required
def upload_attachment(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    file = request.files.get("file")
    version_note = request.form.get("version_note", "").strip()

    if not file or not file.filename:
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    original_name = secure_filename(file.filename)
    if not original_name:
        flash("Invalid filename.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    extension = Path(original_name).suffix.lower()
    if extension not in _allowed_attachment_extensions():
        flash("Unsupported file type for task attachments.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    upload_root = Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    task_upload_dir = upload_root / "tasks" / str(task.id)
    task_upload_dir.mkdir(parents=True, exist_ok=True)

    safe_stem = Path(original_name).stem or "attachment"
    stored_name = f"{safe_stem}_{uuid4().hex[:8]}{extension}"
    relative_path = Path("tasks") / str(task.id) / stored_name
    absolute_path = upload_root / relative_path
    file.save(absolute_path)

    version = TaskAttachment.query.filter_by(task_id=task.id, original_name=original_name).count() + 1
    file_hash = _sha256_for_file(absolute_path)
    attachment = TaskAttachment(
        task_id=task.id,
        filename=relative_path.as_posix(),
        original_name=original_name,
        content_type=file.content_type,
        file_size=absolute_path.stat().st_size,
        file_hash=file_hash,
        version=version,
        version_note=version_note or None,
        uploaded_by=current_user.id,
    )
    db.session.add(attachment)
    db.session.flush()
    db.session.add(
        TaskAttachmentRevision(
            attachment_id=attachment.id,
            version=attachment.version,
            filename=attachment.filename,
            file_size=attachment.file_size,
            file_hash=file_hash,
            version_note=attachment.version_note,
            created_by=current_user.id,
        )
    )
    _log_activity(task, "attachment_uploaded", f"{original_name} (v{version})")
    db.session.commit()

    flash("Attachment uploaded.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/attachments/<int:attachment_id>/download")
@login_required
def download_attachment(task_id, attachment_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.VIEWER)

    attachment = TaskAttachment.query.filter_by(id=attachment_id, task_id=task.id, is_deleted=False).first_or_404()
    file_path = Path(current_app.config.get("UPLOAD_FOLDER", "uploads")) / attachment.filename
    if not file_path.exists():
        abort(404)
    return send_file(file_path, as_attachment=True, download_name=attachment.original_name)


@tasks_bp.route("/<int:task_id>/attachments/<int:attachment_id>/preview")
@login_required
def preview_attachment(task_id, attachment_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.VIEWER)

    attachment = TaskAttachment.query.filter_by(id=attachment_id, task_id=task.id, is_deleted=False).first_or_404()
    file_path = Path(current_app.config.get("UPLOAD_FOLDER", "uploads")) / attachment.filename
    if not file_path.exists():
        abort(404)

    mimetype = attachment.content_type or "application/octet-stream"
    return send_file(file_path, mimetype=mimetype, as_attachment=False, download_name=attachment.original_name)


@tasks_bp.route("/<int:task_id>/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
def delete_attachment(task_id, attachment_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    attachment = TaskAttachment.query.filter_by(id=attachment_id, task_id=task.id, is_deleted=False).first_or_404()
    attachment.is_deleted = True
    attachment.deleted_at = datetime.utcnow()
    _log_activity(task, "attachment_deleted", attachment.original_name)
    db.session.commit()

    flash("Attachment deleted.", "info")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/comment", methods=["POST"])
@login_required
def add_comment(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    content = request.form.get("content", "").strip()
    if not content:
        flash("Comment content is required.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    comment = Comment(content=content, task_id=task.id, author_id=current_user.id)
    db.session.add(comment)

    mentions = _extract_mentions(content)
    mention_suffix = f" (mentions: {', '.join(user.username for user in mentions)})" if mentions else ""
    _log_activity(task, "comment_added", f"Comment added{mention_suffix}")

    for mentioned in mentions:
        _notify_user(
            mentioned.id,
            "You were mentioned",
            f"{current_user.username} mentioned you on task: {task.title}",
            kind="mention",
        )

    db.session.commit()
    flash("Comment added.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/comment/<int:comment_id>/edit", methods=["POST"])
@login_required
def edit_comment(task_id, comment_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    comment = Comment.query.filter_by(id=comment_id, task_id=task.id).first_or_404()
    _ensure_comment_access(comment)

    content = request.form.get("content", "").strip()
    if not content:
        flash("Comment content is required.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    comment.content = content
    mentions = _extract_mentions(content)
    mention_suffix = f" (mentions: {', '.join(user.username for user in mentions)})" if mentions else ""
    _log_activity(task, "comment_edited", f"Comment edited{mention_suffix}")

    for mentioned in mentions:
        _notify_user(
            mentioned.id,
            "You were mentioned",
            f"{current_user.username} mentioned you on task: {task.title}",
            kind="mention",
        )

    db.session.commit()
    flash("Comment updated.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(task_id, comment_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    comment = Comment.query.filter_by(id=comment_id, task_id=task.id).first_or_404()
    _ensure_comment_access(comment)

    db.session.delete(comment)
    _log_activity(task, "comment_deleted", "Comment removed")
    db.session.commit()
    flash("Comment deleted.", "info")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/sprint", methods=["POST"])
@login_required
def assign_sprint(task_id):
    task = Task.query.get_or_404(task_id)
    _require_project_role(task.project_id, ProjectMembershipRole.MEMBER)

    sprint_id_raw = request.form.get("sprint_id", "").strip()
    if not sprint_id_raw:
        task.sprint_id = None
        _log_activity(task, "sprint_unassigned", "Removed from sprint")
    elif sprint_id_raw.isdigit():
        sprint = Sprint.query.get_or_404(int(sprint_id_raw))
        if sprint.project_id != task.project_id:
            flash("Sprint must belong to the same project.", "error")
            return redirect(url_for("tasks.detail", task_id=task.id))
        task.sprint_id = sprint.id
        _log_activity(task, "sprint_assigned", f"Assigned to sprint: {sprint.name}")
    else:
        flash("Invalid sprint selection.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    db.session.commit()
    flash("Sprint assignment updated.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/sprints", methods=["GET", "POST"])
@login_required
def sprints():
    projects = Project.query.order_by(Project.name.asc()).all()
    project_filter = request.args.get("project", "").strip()

    selected_project = Project.query.get(int(project_filter)) if project_filter.isdigit() else None

    if request.method == "POST":
        project_id = request.form.get("project_id", "").strip()
        if not project_id.isdigit():
            flash("Project is required.", "error")
            return redirect(url_for("tasks.sprints"))

        project = Project.query.get_or_404(int(project_id))
        _require_project_role(project.id, ProjectMembershipRole.MANAGER)

        name = request.form.get("name", "").strip()
        if not name:
            flash("Sprint name is required.", "error")
            return redirect(url_for("tasks.sprints", project=project.id))

        sprint = Sprint(
            name=name,
            goal=request.form.get("goal", "").strip() or None,
            project_id=project.id,
            created_by=current_user.id,
            start_date=_parse_date_or_none(request.form.get("start_date", "").strip()),
            end_date=_parse_date_or_none(request.form.get("end_date", "").strip()),
        )
        db.session.add(sprint)
        db.session.commit()
        flash("Sprint created.", "success")
        return redirect(url_for("tasks.sprints", project=project.id))

    sprint_query = Sprint.query.options(joinedload(Sprint.project)).order_by(Sprint.created_at.desc())
    if selected_project:
        sprint_query = sprint_query.filter(Sprint.project_id == selected_project.id)

    sprints_list = sprint_query.all()

    backlog_tasks = []
    if selected_project:
        backlog_tasks = (
            Task.query.filter(Task.project_id == selected_project.id, Task.sprint_id.is_(None))
            .order_by(Task.created_at.desc())
            .all()
        )

    return render_template(
        "tasks/sprints.html",
        projects=projects,
        selected_project=selected_project,
        sprints=sprints_list,
        backlog_tasks=backlog_tasks,
        sprint_status_values=[value.value for value in SprintStatus],
    )


@tasks_bp.route("/sprints/<int:sprint_id>/status", methods=["POST"])
@login_required
def update_sprint_status(sprint_id):
    sprint = Sprint.query.get_or_404(sprint_id)
    _require_project_role(sprint.project_id, ProjectMembershipRole.MANAGER)

    status_raw = request.form.get("status", "").strip().lower()
    try:
        sprint.status = SprintStatus(status_raw)
    except ValueError:
        flash("Invalid sprint status.", "error")
        return redirect(url_for("tasks.sprints", project=sprint.project_id))

    db.session.commit()
    flash("Sprint status updated.", "success")
    return redirect(url_for("tasks.sprints", project=sprint.project_id))


@tasks_bp.route("/notifications")
@login_required
def notifications():
    records = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template("tasks/notifications.html", notifications=records)


@tasks_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    record = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    record.is_read = True
    db.session.commit()
    return redirect(url_for("tasks.notifications"))


@tasks_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("tasks.notifications"))


@tasks_bp.route("/reports")
@login_required
def reports():
    now = datetime.now(UTC).replace(tzinfo=None)
    tasks = Task.query.options(joinedload(Task.activities), joinedload(Task.sprint)).all()

    total_tasks = len(tasks)
    done_tasks = sum(1 for task in tasks if task.status == TaskStatus.DONE)
    overdue_tasks = sum(1 for task in tasks if task.due_date and task.due_date < now and task.status != TaskStatus.DONE)
    total_story_points = sum(task.story_points for task in tasks)
    completed_story_points = sum(task.story_points for task in tasks if task.status == TaskStatus.DONE)

    throughput_window = now - timedelta(days=14)
    throughput = (
        TaskActivity.query.filter(
            TaskActivity.action == "status_changed",
            TaskActivity.details.ilike("%done%"),
            TaskActivity.created_at >= throughput_window,
        ).count()
    )

    cycle_durations = []
    for task in tasks:
        done_event = next(
            (
                event
                for event in task.activities
                if event.action == "status_changed" and (event.details or "").lower().endswith("done")
            ),
            None,
        )
        if done_event:
            cycle_durations.append((done_event.created_at - task.created_at).total_seconds() / 3600)

    avg_cycle_hours = round(sum(cycle_durations) / len(cycle_durations), 2) if cycle_durations else 0

    active_sprints = Sprint.query.filter_by(status=SprintStatus.ACTIVE).all()
    burndown = []
    for sprint in active_sprints:
        sprint_tasks = [task for task in sprint.tasks]
        total = len(sprint_tasks)
        remaining = sum(1 for task in sprint_tasks if task.status != TaskStatus.DONE)
        total_points = sum(task.story_points for task in sprint_tasks)
        remaining_points = sum(task.story_points for task in sprint_tasks if task.status != TaskStatus.DONE)
        burndown.append(
            {
                "sprint": sprint,
                "total": total,
                "remaining": remaining,
                "total_points": total_points,
                "remaining_points": remaining_points,
            }
        )

    closed_sprints = Sprint.query.filter_by(status=SprintStatus.CLOSED).all()
    closed_velocity_points = []
    for sprint in closed_sprints:
        completed_points = sum(task.story_points for task in sprint.tasks if task.status == TaskStatus.DONE)
        closed_velocity_points.append(completed_points)
    avg_velocity_points = (
        round(sum(closed_velocity_points) / len(closed_velocity_points), 2) if closed_velocity_points else 0
    )

    completion_trend = []
    for day_offset in range(6, -1, -1):
        day_start = (now - timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        completed = (
            TaskActivity.query.filter(
                TaskActivity.action == "status_changed",
                TaskActivity.details.ilike("%done%"),
                TaskActivity.created_at >= day_start,
                TaskActivity.created_at < day_end,
            ).count()
        )
        completion_trend.append({"date": day_start.date(), "completed": completed})

    return render_template(
        "tasks/reports.html",
        total_tasks=total_tasks,
        done_tasks=done_tasks,
        overdue_tasks=overdue_tasks,
        total_story_points=total_story_points,
        completed_story_points=completed_story_points,
        throughput=throughput,
        avg_cycle_hours=avg_cycle_hours,
        avg_velocity_points=avg_velocity_points,
        burndown=burndown,
        completion_trend=completion_trend,
    )


@tasks_bp.route("/integrations", methods=["GET", "POST"])
@login_required
def integrations():
    new_token_value = None

    if request.method == "POST":
        action = request.form.get("action", "").strip()
        if action == "create_token":
            name = request.form.get("name", "").strip() or "API Token"
            token_value = ApiToken.generate_value()
            token = ApiToken(user_id=current_user.id, name=name, token=token_value)
            db.session.add(token)
            db.session.commit()
            new_token_value = token_value
            flash("API token created. Save it now.", "success")
        elif action == "revoke_token":
            token_id = request.form.get("token_id", "").strip()
            if token_id.isdigit():
                token = ApiToken.query.filter_by(id=int(token_id), user_id=current_user.id).first_or_404()
                token.is_active = False
                db.session.commit()
                flash("API token revoked.", "info")

    tokens = ApiToken.query.filter_by(user_id=current_user.id).order_by(ApiToken.created_at.desc()).all()
    return render_template("tasks/integrations.html", tokens=tokens, new_token_value=new_token_value)


@tasks_bp.route("/export.csv")
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "title",
        "description",
        "project_id",
        "assignee_id",
        "status",
        "priority",
        "due_date",
        "story_points",
        "progress",
        "labels",
    ])

    for task in Task.query.order_by(Task.id.asc()).all():
        labels = ",".join(label.name for label in task.labels)
        writer.writerow(
            [
                task.id,
                task.title,
                task.description or "",
                task.project_id,
                task.assignee_id or "",
                task.status.value,
                task.priority.value,
                task.due_date.strftime("%Y-%m-%d") if task.due_date else "",
                task.story_points,
                task.progress,
                labels,
            ]
        )

    data = output.getvalue()
    output.close()
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks_export.csv"},
    )


@tasks_bp.route("/import", methods=["POST"])
@login_required
def import_csv():
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".csv"):
        flash("Please upload a CSV file.", "error")
        return redirect(url_for("tasks.index"))

    stream = io.StringIO(file.stream.read().decode("utf-8", errors="ignore"))
    reader = csv.DictReader(stream)

    imported_count = 0
    for row in reader:
        title = (row.get("title") or "").strip()
        project_id_raw = (row.get("project_id") or "").strip()
        if not title or not project_id_raw.isdigit():
            continue

        project_id = int(project_id_raw)
        _require_project_role(project_id, ProjectMembershipRole.MEMBER)

        try:
            status = TaskStatus((row.get("status") or TaskStatus.TODO.value).strip().lower())
        except ValueError:
            status = TaskStatus.TODO

        try:
            priority = TaskPriority((row.get("priority") or TaskPriority.MEDIUM.value).strip().lower())
        except ValueError:
            priority = TaskPriority.MEDIUM

        due_date = _parse_due_date_or_none((row.get("due_date") or "").strip())
        assignee_raw = (row.get("assignee_id") or "").strip()

        task = Task(
            title=title,
            description=(row.get("description") or "").strip(),
            project_id=project_id,
            assignee_id=int(assignee_raw) if assignee_raw.isdigit() else None,
            status=status,
            priority=priority,
            due_date=due_date,
            story_points=_safe_story_points(row.get("story_points") or "0"),
            progress=_safe_progress(row.get("progress") or "0"),
        )
        db.session.add(task)
        db.session.flush()
        _set_task_labels(task, (row.get("labels") or "").strip())
        _log_activity(task, "task_imported", "Imported from CSV")
        imported_count += 1

    db.session.commit()
    flash(f"Imported {imported_count} task(s) from CSV.", "success")
    return redirect(url_for("tasks.index"))


@tasks_bp.route("/webhooks/events", methods=["POST"])
def webhook_events():
    token = request.headers.get("X-Api-Token") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    api_token = ApiToken.query.filter_by(token=token, is_active=True).first() if token else None

    if not api_token:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    api_token.last_used_at = datetime.utcnow()

    payload = request.get_json(silent=True) or {}
    event = str(payload.get("event", "")).strip().lower()

    if event == "task.create":
        title = str(payload.get("title", "")).strip()
        project_id = int(payload.get("project_id")) if str(payload.get("project_id", "")).isdigit() else None
        parent_task_id = int(payload.get("parent_task_id")) if str(payload.get("parent_task_id", "")).isdigit() else None
        if not title or project_id is None:
            return jsonify({"success": False, "error": "Invalid task.create payload"}), 400

        if parent_task_id is not None:
            parent_task = Task.query.get(parent_task_id)
            if not parent_task:
                return jsonify({"success": False, "error": "Parent task not found"}), 400
            if parent_task.project_id != project_id:
                return jsonify({"success": False, "error": "Parent task must belong to the same project"}), 400

        task = Task(
            title=title,
            description=str(payload.get("description", "")).strip(),
            project_id=project_id,
            parent_task_id=parent_task_id,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            progress=0,
        )
        db.session.add(task)
        db.session.flush()
        _log_activity(task, "task_created", "Created by webhook")
        if parent_task_id:
            _sync_parent_rollups(parent_ids={parent_task_id})
        db.session.commit()
        return jsonify({"success": True, "task_id": task.id})

    if event == "task.update_status":
        task_id = int(payload.get("task_id")) if str(payload.get("task_id", "")).isdigit() else None
        status_raw = str(payload.get("status", "")).strip().lower()
        if task_id is None:
            return jsonify({"success": False, "error": "Invalid task id"}), 400

        task = Task.query.get_or_404(task_id)
        try:
            requested_status = TaskStatus(status_raw)
        except ValueError:
            return jsonify({"success": False, "error": "Invalid status"}), 400

        if _has_unfinished_transition_requirements(task, requested_status):
            return jsonify(
                {
                    "success": False,
                    "error": "Cannot move task while blockers or subtasks are unfinished",
                }
            ), 409

        task.status = requested_status

        _log_activity(task, "status_changed", f"Status changed to {task.status.value} by webhook")
        _sync_parent_rollups(task=task)
        db.session.commit()
        return jsonify({"success": True, "task_id": task.id, "status": task.status.value})

    db.session.commit()
    return jsonify({"success": False, "error": "Unsupported event"}), 400


@tasks_bp.route("/automation", methods=["POST"])
@login_required
def create_automation_rule():
    project_id_raw = request.form.get("project_id", "").strip()
    if not project_id_raw.isdigit():
        flash("Project is required for automation rule.", "error")
        return redirect(url_for("projects.index"))

    project_id = int(project_id_raw)
    _require_project_role(project_id, ProjectMembershipRole.MANAGER)

    trigger_type = request.form.get("trigger_type", "").strip().lower()
    action_type = request.form.get("action_type", "").strip().lower()

    if trigger_type not in {"status_changed", "priority_changed", "task_updated"}:
        flash("Invalid trigger type.", "error")
        return redirect(url_for("projects.detail", project_id=project_id, tab="team"))

    if action_type not in {"assign_user", "add_label", "set_due_days", "set_priority"}:
        flash("Invalid action type.", "error")
        return redirect(url_for("projects.detail", project_id=project_id, tab="team"))

    rule = AutomationRule(
        project_id=project_id,
        trigger_type=trigger_type,
        condition_value=request.form.get("condition_value", "").strip() or None,
        action_type=action_type,
        action_value=request.form.get("action_value", "").strip() or None,
    )
    db.session.add(rule)
    db.session.commit()
    flash("Automation rule created.", "success")
    return redirect(url_for("projects.detail", project_id=project_id, tab="team"))


@tasks_bp.route("/automation/<int:rule_id>/toggle", methods=["POST"])
@login_required
def toggle_automation_rule(rule_id):
    rule = AutomationRule.query.get_or_404(rule_id)
    _require_project_role(rule.project_id, ProjectMembershipRole.MANAGER)

    rule.is_active = not rule.is_active
    db.session.commit()
    flash("Automation rule updated.", "success")
    return redirect(url_for("projects.detail", project_id=rule.project_id, tab="team"))


@tasks_bp.route("/automation/<int:rule_id>/delete", methods=["POST"])
@login_required
def delete_automation_rule(rule_id):
    rule = AutomationRule.query.get_or_404(rule_id)
    _require_project_role(rule.project_id, ProjectMembershipRole.MANAGER)

    project_id = rule.project_id
    db.session.delete(rule)
    db.session.commit()
    flash("Automation rule deleted.", "info")
    return redirect(url_for("projects.detail", project_id=project_id, tab="team"))


@tasks_bp.app_template_filter("mentionize")
def mentionize_filter(value):
    text = value or ""

    def repl(match):
        username = match.group(1)
        return f'<span class="font-semibold text-primary">@{username}</span>'

    return re.sub(r"@([A-Za-z0-9_.-]+)", repl, text)


def _apply_task_updates(task, payload, allow_partial):
    changed_fields = []
    previous = {
        "assignee_id": task.assignee_id,
        "due_date": task.due_date,
        "status": task.status,
        "priority": task.priority,
        "parent_task_id": task.parent_task_id,
    }

    if not allow_partial or "title" in payload:
        title = (payload.get("title") or "").strip()
        if not title:
            raise ValueError("Task title is required.")
        if task.title != title:
            task.title = title
            changed_fields.append("title")

    if not allow_partial or "description" in payload:
        description = (payload.get("description") or "").strip()
        if task.description != description:
            task.description = description
            changed_fields.append("description")

    if not allow_partial or "project_id" in payload:
        project_id = str(payload.get("project_id") or "").strip()
        if not project_id.isdigit():
            raise ValueError("Project is required.")
        project_id_value = int(project_id)
        _require_project_role(project_id_value, ProjectMembershipRole.MEMBER)
        if task.project_id != project_id_value:
            task.project_id = project_id_value
            changed_fields.append("project")

        if task.parent_task_id is not None and task.parent_task and task.parent_task.project_id != task.project_id:
            task.parent_task_id = None
            if "parent task" not in changed_fields:
                changed_fields.append("parent task")

    if not allow_partial or "parent_task_id" in payload:
        parent_task_raw = payload.get("parent_task_id")
        parent_task_id = _parse_parent_task_id(parent_task_raw)

        if parent_task_raw not in (None, "") and parent_task_id is None:
            raise ValueError("Invalid parent task selection.")

        if parent_task_id == task.id:
            raise ValueError("Task cannot be its own parent.")

        if parent_task_id is not None:
            parent = Task.query.get(parent_task_id)
            if not parent:
                raise ValueError("Selected parent task does not exist.")
            if parent.project_id != task.project_id:
                raise ValueError("Parent task must belong to the same project.")
            if _task_is_descendant(candidate_parent=parent, task=task):
                raise ValueError("Parent task cannot be a descendant of this task.")

        if task.parent_task_id != parent_task_id:
            task.parent_task_id = parent_task_id
            changed_fields.append("parent task")

    if not allow_partial or "assignee_id" in payload:
        assignee_raw = str(payload.get("assignee_id") or "").strip()
        assignee_value = int(assignee_raw) if assignee_raw.isdigit() else None
        if task.assignee_id != assignee_value:
            task.assignee_id = assignee_value
            changed_fields.append("assignee")

    if not allow_partial or "priority" in payload:
        priority_raw = str(payload.get("priority") or task.priority.value).strip().lower()
        try:
            priority_value = TaskPriority(priority_raw)
        except ValueError as exc:
            raise ValueError("Invalid priority value.") from exc

        if task.priority != priority_value:
            task.priority = priority_value
            changed_fields.append("priority")

    if not allow_partial or "status" in payload:
        status_raw = str(payload.get("status") or task.status.value).strip().lower()
        try:
            status_value = TaskStatus(status_raw)
        except ValueError as exc:
            raise ValueError("Invalid status value.") from exc

        if _has_unfinished_transition_requirements(task, status_value):
            raise ValueError("Task has unfinished dependencies or subtasks and cannot be moved to in_review or done.")

        if task.status != status_value:
            task.status = status_value
            changed_fields.append("status")

    if not allow_partial or "due_date" in payload:
        due_date_raw = str(payload.get("due_date") or "").strip()
        due_date = _parse_due_date_or_none(due_date_raw)
        if due_date_raw and due_date is None:
            raise ValueError("Invalid due date format.")
        if task.due_date != due_date:
            task.due_date = due_date
            changed_fields.append("due date")

    if not allow_partial or "progress" in payload:
        progress_raw = str(payload.get("progress") or "0").strip()
        progress = _safe_progress(progress_raw)
        if task.progress != progress:
            task.progress = progress
            changed_fields.append("progress")

    if not allow_partial or "story_points" in payload:
        story_points_raw = str(payload.get("story_points") or "0").strip()
        story_points = _safe_story_points(story_points_raw)
        if task.story_points != story_points:
            task.story_points = story_points
            changed_fields.append("story points")

    if "labels" in payload:
        labels_changed = _set_task_labels(task, payload.get("labels"))
        if labels_changed:
            changed_fields.append("labels")

    return changed_fields, previous


def _parse_parent_task_id(value):
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if not raw.isdigit():
        return None
    return int(raw)


def _parent_candidates(project_id, exclude_task_id=None):
    query = Task.query.filter(Task.project_id == project_id)
    if exclude_task_id is not None:
        query = query.filter(Task.id != exclude_task_id)
    return query.order_by(Task.created_at.desc()).all()


def _task_is_descendant(candidate_parent, task):
    cursor = candidate_parent
    visited = set()
    while cursor is not None:
        if cursor.id in visited:
            return True
        visited.add(cursor.id)
        if cursor.id == task.id:
            return True
        cursor = cursor.parent_task
    return False


def _build_dependency_mermaid(project_id, current_task_id):
    tasks = (
        Task.query.options(joinedload(Task.blocking_tasks), joinedload(Task.blocked_tasks))
        .filter(Task.project_id == project_id)
        .all()
    )

    nodes = []
    edges = []
    for task in tasks:
        safe_title = (task.title or "").replace('"', "'")
        label = f"#{task.id} {safe_title[:42]}"
        nodes.append(f'T{task.id}["{label}"]')
        for blocker in task.blocking_tasks:
            edges.append(f"T{blocker.id} --> T{task.id}")

    if not edges:
        return ""

    graph_lines = ["graph TD"]
    graph_lines.extend(nodes)
    graph_lines.extend(edges)
    graph_lines.append(f"classDef current fill:#1d4ed8,color:#fff,stroke:#1e40af,stroke-width:2px")
    graph_lines.append(f"class T{current_task_id} current")
    return "\n".join(graph_lines)


def _set_task_labels(task, raw_value):
    names = []
    for chunk in (raw_value or "").split(","):
        cleaned = chunk.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered not in [name.lower() for name in names]:
            names.append(cleaned)

    desired = []

    for name in names:
        found = TaskLabel.query.filter(func.lower(TaskLabel.name) == name.lower()).first()
        if not found:
            found = TaskLabel(name=name, color=_label_color(name))
            db.session.add(found)
            db.session.flush()
        desired.append(found)

    current_ids = sorted(label.id for label in task.labels)
    desired_ids = sorted(label.id for label in desired)

    task.labels = desired
    return current_ids != desired_ids


def _label_color(name):
    palette = ["blue", "emerald", "amber", "violet", "rose", "cyan", "orange", "slate"]
    return palette[hash(name.lower()) % len(palette)]


def _extract_mentions(content):
    usernames = {match.group(1).lower() for match in re.finditer(r"@([A-Za-z0-9_.-]+)", content or "")}
    if not usernames:
        return []

    users = User.query.filter(func.lower(User.username).in_(usernames)).order_by(User.username.asc()).all()
    return users


def _unfinished_blockers(task):
    return [blocker for blocker in task.blocking_tasks if blocker.status != TaskStatus.DONE]


def _unfinished_subtasks(task):
    return [subtask for subtask in task.subtasks if subtask.status != TaskStatus.DONE]


def _has_unfinished_transition_requirements(task, next_status):
    if next_status not in {TaskStatus.IN_REVIEW, TaskStatus.DONE}:
        return False
    return bool(_unfinished_blockers(task) or _unfinished_subtasks(task))


def _sync_parent_rollups(task=None, previous_parent_id=None, parent_ids=None):
    affected_parent_ids = set(parent_ids or [])

    if task is not None and task.parent_task_id:
        affected_parent_ids.add(task.parent_task_id)
    if previous_parent_id:
        affected_parent_ids.add(previous_parent_id)

    snapshots_by_id = {}
    for parent_id in affected_parent_ids:
        for snapshot in _rollup_parent_chain(parent_id):
            snapshots_by_id[snapshot["id"]] = snapshot

    return list(snapshots_by_id.values())


def _rollup_parent_chain(parent_id):
    visited = set()
    current = Task.query.get(parent_id)
    snapshots = []

    while current is not None and current.id not in visited:
        visited.add(current.id)
        subtasks = Task.query.filter_by(parent_task_id=current.id).all()

        if subtasks:
            done_count = sum(1 for subtask in subtasks if subtask.status == TaskStatus.DONE)
            progress_rollup = int(round((done_count / len(subtasks)) * 100))
            has_blockers = bool(_unfinished_blockers(current))

            if current.progress != progress_rollup:
                current.progress = progress_rollup
                _log_activity(current, "subtask_progress_rollup", f"Progress rolled up to {progress_rollup}% from subtasks")

            if done_count == len(subtasks) and not has_blockers and current.status != TaskStatus.DONE:
                current.status = TaskStatus.DONE
                _log_activity(current, "subtasks_completed", "All subtasks completed; parent task auto-closed")
            elif (done_count < len(subtasks) or has_blockers) and current.status == TaskStatus.DONE:
                current.status = TaskStatus.IN_PROGRESS
                _log_activity(current, "subtasks_reopened", "Subtasks reopened or added; parent task moved back to in progress")

            snapshots.append(
                {
                    "id": current.id,
                    "status": current.status.value,
                    "progress": current.progress,
                    "subtask_done": done_count,
                    "subtask_total": len(subtasks),
                }
            )

        current = current.parent_task

    return snapshots


def _creates_dependency_cycle(blocker, target):
    stack = [target]
    visited = set()

    while stack:
        current = stack.pop()
        if current.id in visited:
            continue
        visited.add(current.id)

        if current.id == blocker.id:
            return True

        stack.extend(current.blocked_tasks)

    return False


def _ensure_comment_access(comment):
    is_admin_like = current_user.role.value in {"admin", "owner"}
    if comment.author_id != current_user.id and not is_admin_like:
        abort(403)


def _log_activity(task, action, details=""):
    activity = TaskActivity(
        task_id=task.id,
        actor_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        details=details,
    )
    db.session.add(activity)


def _safe_progress(value):
    try:
        progress = int(value)
    except (TypeError, ValueError):
        return 0

    return max(0, min(progress, 100))


def _safe_story_points(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0

    return max(parsed, 0)


def _safe_int_nullable(value):
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        return None
    try:
        parsed = int(stripped)
    except ValueError:
        return None
    return max(parsed, 0)


def _parse_due_date_or_none(value):
    if not value:
        return None

    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def _parse_date_or_none(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _allowed_attachment_extensions():
    return {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".webp"}


def _sha256_for_file(file_path):
    hasher = hashlib.sha256()
    with file_path.open("rb") as file_handle:
        while True:
            chunk = file_handle.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _parse_document_ref(value):
    raw = (value or "").strip()
    if not raw:
        return None, None

    parts = raw.split(":", 1)
    if not parts[0].isdigit():
        return None, None

    document_id = int(parts[0])
    expected_lock_version = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else None
    return document_id, expected_lock_version


def _notify_user(user_id, title, message, kind="event"):
    if not user_id:
        return
    db.session.add(Notification(user_id=user_id, channel="in_app", kind=kind, title=title, message=message))
    db.session.add(Notification(user_id=user_id, channel="email", kind=kind, title=title, message=message))


def _notify_assignment_if_needed(task, previous_assignee_id):
    if task.assignee_id and task.assignee_id != previous_assignee_id:
        _notify_user(task.assignee_id, "Task assigned", f"You were assigned to task: {task.title}", kind="assignment")


def _notify_due_date_if_needed(task, previous_due_date):
    if not task.due_date:
        return
    if previous_due_date == task.due_date:
        return

    now = datetime.now(UTC).replace(tzinfo=None)
    if task.due_date <= now + timedelta(days=2) and task.assignee_id:
        _notify_user(task.assignee_id, "Due date reminder", f"Task '{task.title}' is due soon.", kind="due_date")


def _notify_watchers(task, title, message):
    watcher_ids = [watch.user_id for watch in task.watchers if watch.user_id != current_user.id]
    for user_id in watcher_ids:
        _notify_user(user_id, title, message, kind="watch")


def _run_automation_rules(task, changed_fields):
    trigger_types = set()
    if "status" in changed_fields:
        trigger_types.add("status_changed")
    if "priority" in changed_fields:
        trigger_types.add("priority_changed")
    if changed_fields:
        trigger_types.add("task_updated")

    if not trigger_types:
        return

    rules = AutomationRule.query.filter_by(project_id=task.project_id, is_active=True).all()
    for rule in rules:
        if rule.trigger_type not in trigger_types:
            continue

        if rule.trigger_type == "status_changed" and rule.condition_value and task.status.value != rule.condition_value:
            continue
        if rule.trigger_type == "priority_changed" and rule.condition_value and task.priority.value != rule.condition_value:
            continue

        if rule.action_type == "assign_user":
            if str(rule.action_value or "").isdigit():
                task.assignee_id = int(rule.action_value)
        elif rule.action_type == "add_label":
            if rule.action_value:
                merged = ",".join([label.name for label in task.labels] + [rule.action_value])
                _set_task_labels(task, merged)
        elif rule.action_type == "set_due_days":
            if str(rule.action_value or "").isdigit():
                task.due_date = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=int(rule.action_value))
        elif rule.action_type == "set_priority":
            try:
                task.priority = TaskPriority(str(rule.action_value or "").lower())
            except ValueError:
                continue

        _log_activity(task, "automation_applied", f"Rule #{rule.id} applied")


def _require_project_role(project_id, required_role):
    if current_user.role.value in {"admin", "owner"}:
        return

    membership = ProjectMembership.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    has_memberships = ProjectMembership.query.filter_by(project_id=project_id).count() > 0

    if not has_memberships:
        return
    if not membership:
        abort(403)

    rank = {
        ProjectMembershipRole.VIEWER: 1,
        ProjectMembershipRole.MEMBER: 2,
        ProjectMembershipRole.MANAGER: 3,
        ProjectMembershipRole.ADMIN: 4,
    }

    if rank[membership.role] < rank[required_role]:
        abort(403)
