from datetime import datetime, timedelta, timezone

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, subqueryload

from ..extensions import db
from ..models.document import Document
from ..models.planning import ProjectMembership
from ..models.project import Project, ProjectStatus
from ..models.task import Task, TaskPriority, TaskStatus
from ..models.user import user_has_right


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return render_template("landing.html")


@dashboard_bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()

    projects = []
    tasks = []
    documents = []
    visible_project_ids = _visible_project_ids_query()

    if q:
        pattern = f"%{q}%"
        projects = (
            Project.query
            .filter(or_(Project.name.ilike(pattern), Project.description.ilike(pattern)))
            .filter(Project.id.in_(visible_project_ids))
            .order_by(Project.updated_at.desc())
            .limit(5)
            .all()
        )
        tasks = (
            Task.query.options(joinedload(Task.assignee), joinedload(Task.project))
            .filter(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
            .filter(Task.project_id.in_(visible_project_ids))
            .order_by(Task.created_at.desc())
            .limit(5)
            .all()
        )
        documents = (
            Document.query.options(joinedload(Document.project), joinedload(Document.uploader))
            .filter(or_(Document.original_name.ilike(pattern), Document.extracted_text.ilike(pattern)))
            .filter(Document.project_id.in_(visible_project_ids))
            .order_by(Document.created_at.desc())
            .limit(5)
            .all()
        )

    return render_template(
        "dashboard/search.html",
        q=q,
        projects=projects,
        tasks=tasks,
        documents=documents,
        total_results=len(projects) + len(tasks) + len(documents),
    )


@dashboard_bp.route("/dashboard")
@login_required
def index():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_label = now.strftime("%d %b %Y")
    soon_threshold = now + timedelta(days=7)
    visible_project_ids = _visible_project_ids_query()

    active_project_count = Project.query.filter(Project.id.in_(visible_project_ids), Project.status == ProjectStatus.ACTIVE).count()
    upcoming_deadline_count = Task.query.filter(
        Task.project_id.in_(visible_project_ids),
        Task.due_date.isnot(None),
        Task.due_date >= now,
        Task.due_date <= soon_threshold,
        Task.status != TaskStatus.DONE,
    ).count()

    tomorrow_end = now + timedelta(days=1)
    week_end = now + timedelta(days=7)
    week_start = now - timedelta(days=7)

    overdue_count = Task.query.filter(
        Task.project_id.in_(visible_project_ids),
        Task.due_date.isnot(None),
        Task.due_date < now,
        Task.status != TaskStatus.DONE,
    ).count()

    due_soon_count = Task.query.filter(
        Task.project_id.in_(visible_project_ids),
        Task.due_date.isnot(None),
        Task.due_date >= now,
        Task.due_date <= tomorrow_end,
        Task.status != TaskStatus.DONE,
    ).count()

    due_this_week_count = Task.query.filter(
        Task.project_id.in_(visible_project_ids),
        Task.due_date.isnot(None),
        Task.due_date > tomorrow_end,
        Task.due_date <= week_end,
        Task.status != TaskStatus.DONE,
    ).count()

    done_recently_count = Task.query.filter(
        Task.project_id.in_(visible_project_ids),
        Task.status == TaskStatus.DONE,
        Task.created_at >= week_start,
    ).count()

    high_no_due_count = Task.query.filter(
        Task.project_id.in_(visible_project_ids),
        Task.priority.in_([TaskPriority.HIGH, TaskPriority.CRITICAL]),
        Task.due_date.is_(None),
        Task.status != TaskStatus.DONE,
    ).count()

    ai_insights = []

    if overdue_count:
        task_word = "task" if overdue_count == 1 else "tasks"
        ai_insights.append({
            "type_label": "Risk Detection",
            "title": f"{overdue_count} overdue {task_word}",
            "description": f"{overdue_count} {task_word} passed their due date without being completed.",
            "timestamp": "Now",
            "action_label": "View Tasks",
            "action_url": "/tasks/?quick=overdue",
            "tone": "default",
        })

    if due_soon_count:
        task_word = "task" if due_soon_count == 1 else "tasks"
        ai_insights.append({
            "type_label": "Deadline Alert",
            "title": f"{due_soon_count} {task_word} due today or tomorrow",
            "description": f"{due_soon_count} {task_word} need attention in the next 24 hours.",
            "timestamp": "Now",
            "action_label": "View Tasks",
            "action_url": "/tasks/?quick=due_week",
            "tone": "primary",
        })

    if due_this_week_count:
        task_word = "task" if due_this_week_count == 1 else "tasks"
        ai_insights.append({
            "type_label": "Upcoming Work",
            "title": f"{due_this_week_count} {task_word} due this week",
            "description": f"Plan ahead — {due_this_week_count} {task_word} are scheduled for the next 7 days.",
            "timestamp": "Now",
            "action_label": "View Tasks",
            "action_url": "/tasks/?quick=due_week",
            "tone": "indigo",
        })

    if done_recently_count:
        task_word = "task" if done_recently_count == 1 else "tasks"
        ai_insights.append({
            "type_label": "Achievement",
            "title": f"{done_recently_count} {task_word} completed this week",
            "description": f"Great progress — {done_recently_count} {task_word} were marked done in the last 7 days.",
            "timestamp": "This week",
            "action_label": "View Tasks",
            "action_url": "/tasks/?status=done",
            "tone": "emerald",
        })

    if high_no_due_count and len(ai_insights) < 4:
        task_word = "task" if high_no_due_count == 1 else "tasks"
        ai_insights.append({
            "type_label": "Attention Needed",
            "title": f"{high_no_due_count} high-priority {task_word} without a deadline",
            "description": f"{high_no_due_count} high or critical priority {task_word} have no due date set.",
            "timestamp": "Now",
            "action_label": "View Tasks",
            "action_url": "/tasks/?quick=high_priority",
            "tone": "indigo",
        })

    ai_insights = ai_insights[:4]
    ai_insight_count = len(ai_insights)

    projects = (
        Project.query.filter(Project.id.in_(visible_project_ids), Project.status == ProjectStatus.ACTIVE)
        .options(subqueryload(Project.tasks).joinedload(Task.assignee))
        .order_by(Project.updated_at.desc())
        .limit(3)
        .all()
    )
    project_rows = []
    for project in projects:
        project_progress = _calculate_project_progress(project.tasks)
        due_label = "Due soon"
        project_due_dates = [task.due_date for task in project.tasks if task.due_date]
        if project_due_dates:
            next_due = min(project_due_dates)
            days_left = (next_due.date() - now.date()).days
            if days_left <= 0:
                due_label = "Due today"
            elif days_left == 1:
                due_label = "Due tomorrow"
            else:
                due_label = f"Due in {days_left} days"

        if project_progress >= 80:
            dot_color = "bg-emerald-500"
        elif project_progress >= 50:
            dot_color = "bg-primary"
        else:
            dot_color = "bg-orange-500"

        team_names = []
        for task in project.tasks:
            if task.assignee and task.assignee.username not in team_names:
                team_names.append(task.assignee.username)
            if len(team_names) >= 3:
                break

        project_rows.append(
            {
                "id": project.id,
                "name": project.name,
                "progress": project_progress,
                "due_label": due_label,
                "dot_color": dot_color,
                "team": team_names,
            }
        )

    recent_tasks = (
        Task.query.options(joinedload(Task.assignee))
        .filter(Task.project_id.in_(visible_project_ids))
        .order_by(Task.created_at.desc())
        .limit(3)
        .all()
    )
    recent_documents = (
        Document.query.options(joinedload(Document.uploader))
        .filter(Document.project_id.in_(visible_project_ids))
        .order_by(Document.created_at.desc())
        .limit(3)
        .all()
    )

    return render_template(
        "dashboard/index.html",
        active_project_count=active_project_count,
        upcoming_deadline_count=upcoming_deadline_count,
        ai_insight_count=ai_insight_count,
        today_label=today_label,
        top_projects=project_rows,
        recent_tasks=recent_tasks,
        recent_documents=recent_documents,
        ai_insights=ai_insights,
        TaskStatus=TaskStatus,
        TaskPriority=TaskPriority,
    )


def _visible_project_ids_query():
    if user_has_right(current_user, "view_all_projects"):
        return db.session.query(Project.id)

    membership_project_ids = db.session.query(ProjectMembership.project_id).filter_by(user_id=current_user.id)
    return db.session.query(Project.id).filter(
        or_(
            Project.owner_id == current_user.id,
            Project.id.in_(membership_project_ids),
        )
    )


def _calculate_project_progress(tasks):
    if not tasks:
        return 0

    status_defaults = {
        TaskStatus.TODO: 0,
        TaskStatus.IN_PROGRESS: 50,
        TaskStatus.IN_REVIEW: 75,
        TaskStatus.DONE: 100,
    }

    total = 0
    for task in tasks:
        explicit_progress = max(0, min(int(getattr(task, "progress", 0) or 0), 100))
        status_progress = status_defaults.get(task.status, 0)
        total += max(explicit_progress, status_progress)

    return round(total / len(tasks))
