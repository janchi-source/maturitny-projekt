from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template
from flask_login import login_required

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

    ai_insights = [
        {
            "type_label": "Risk Detection",
            "title": "Contract clause mismatch in Project Delta",
            "description": "AI detected a conflict between the vendor MSA and recent scope amendments.",
            "timestamp": "2m ago",
            "action_label": "Review Diff",
            "tone": "primary",
        },
        {
            "type_label": "Summarization",
            "title": "Technical Spec V3 Summary",
            "description": "Key takeaway: Required latency reduced from 200ms to 50ms for AI processing nodes.",
            "timestamp": "1h ago",
            "action_label": "Open Summary",
            "tone": "indigo",
        },
        {
            "type_label": "Opportunity",
            "title": "Resource Optimization Identified",
            "description": "AI suggests reallocating 2 backend devs from project Beta to Alpha based on task velocity.",
            "timestamp": "4h ago",
            "action_label": "View Suggestion",
            "tone": "emerald",
        },
    ]
    ai_insight_count = len(ai_insights)

    projects = (
        Project.query.filter(Project.status == ProjectStatus.ACTIVE)
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
                "name": project.name,
                "progress": project.progress,
                "due_label": due_label,
                "dot_color": dot_color,
                "team": team_names,
            }
        )

    recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(3).all()
    recent_documents = Document.query.order_by(Document.created_at.desc()).limit(3).all()

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
