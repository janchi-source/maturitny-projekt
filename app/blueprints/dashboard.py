from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy.orm import joinedload, subqueryload

from ..models.document import Document
from ..models.project import Project, ProjectStatus
from ..models.task import Task, TaskPriority, TaskStatus


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    soon_threshold = now + timedelta(days=7)

    active_project_count = Project.query.filter(Project.status == ProjectStatus.ACTIVE).count()
    upcoming_deadline_count = Task.query.filter(
        Task.due_date.isnot(None),
        Task.due_date >= now,
        Task.due_date <= soon_threshold,
        Task.status != TaskStatus.DONE,
    ).count()

    tomorrow_end = now + timedelta(days=1)
    week_end = now + timedelta(days=7)
    week_start = now - timedelta(days=7)

    overdue_count = Task.query.filter(
        Task.due_date.isnot(None),
        Task.due_date < now,
        Task.status != TaskStatus.DONE,
    ).count()

    due_soon_count = Task.query.filter(
        Task.due_date.isnot(None),
        Task.due_date >= now,
        Task.due_date <= tomorrow_end,
        Task.status != TaskStatus.DONE,
    ).count()

    due_this_week_count = Task.query.filter(
        Task.due_date.isnot(None),
        Task.due_date > tomorrow_end,
        Task.due_date <= week_end,
        Task.status != TaskStatus.DONE,
    ).count()

    done_recently_count = Task.query.filter(
        Task.status == TaskStatus.DONE,
        Task.created_at >= week_start,
    ).count()

    high_no_due_count = Task.query.filter(
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
        Project.query.filter(Project.status == ProjectStatus.ACTIVE)
        .options(subqueryload(Project.tasks).joinedload(Task.assignee))
        .order_by(Project.updated_at.desc())
        .limit(3)
        .all()
    )
    project_rows = []
    for project in projects:
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

        if project.progress >= 80:
            dot_color = "bg-emerald-500"
        elif project.progress >= 50:
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
                "progress": project.progress,
                "due_label": due_label,
                "dot_color": dot_color,
                "team": team_names,
            }
        )

    recent_tasks = (
        Task.query.options(joinedload(Task.assignee))
        .order_by(Task.created_at.desc())
        .limit(3)
        .all()
    )
    recent_documents = (
        Document.query.options(joinedload(Document.uploader))
        .order_by(Document.created_at.desc())
        .limit(3)
        .all()
    )

    return render_template(
        "dashboard/index.html",
        active_project_count=active_project_count,
        upcoming_deadline_count=upcoming_deadline_count,
        ai_insight_count=ai_insight_count,
        top_projects=project_rows,
        recent_tasks=recent_tasks,
        recent_documents=recent_documents,
        ai_insights=ai_insights,
        TaskStatus=TaskStatus,
        TaskPriority=TaskPriority,
    )
