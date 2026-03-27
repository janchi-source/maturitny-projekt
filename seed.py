from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.ai_chat import ChatMessage, ChatMessageRole, ChatSession
from app.models.document import Document, DocumentType
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole


def get_or_create_user(username, email, role):
    user = User.query.filter_by(email=email).first()
    if user:
        updated = False
        if user.username != username:
            user.username = username
            updated = True
        if user.role != role:
            user.role = role
            updated = True
        if updated:
            db.session.commit()
        return user

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash("Secret123!"),
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return user


def get_or_create_project(name, description, status, progress, owner_id):
    project = Project.query.filter_by(name=name).first()
    if project:
        return project

    project = Project(
        name=name,
        description=description,
        status=status,
        progress=progress,
        owner_id=owner_id,
    )
    db.session.add(project)
    db.session.commit()
    return project


def main():
    app = create_app()
    with app.app_context():
        admin = get_or_create_user("admin", "admin@promat.local", UserRole.ADMIN)
        member = get_or_create_user("member", "member@promat.local", UserRole.COORDINATOR)

        projects = [
            get_or_create_project(
                "Litigation AI Rollout",
                "Deploy AI-assisted legal document workflows across active litigations.",
                ProjectStatus.ACTIVE,
                68,
                admin.id,
            ),
            get_or_create_project(
                "Compliance Archive Migration",
                "Migrate historical compliance files into centralized repository.",
                ProjectStatus.ACTIVE,
                35,
                admin.id,
            ),
            get_or_create_project(
                "Contract Review Automation",
                "Pilot automated clause extraction and risk scoring.",
                ProjectStatus.COMPLETED,
                100,
                admin.id,
            ),
        ]

        if Task.query.count() < 5:
            tasks_seed = [
                ("Prepare hearing summary model", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, 55, projects[0].id, member.id, 6),
                ("Validate document tagging policy", TaskStatus.IN_REVIEW, TaskPriority.MEDIUM, 80, projects[0].id, admin.id, 3),
                ("Reconcile migrated archives", TaskStatus.TODO, TaskPriority.CRITICAL, 10, projects[1].id, member.id, 10),
                ("Create contract benchmark set", TaskStatus.DONE, TaskPriority.MEDIUM, 100, projects[2].id, admin.id, -1),
                ("Draft rollout checklist", TaskStatus.TODO, TaskPriority.LOW, 15, projects[1].id, None, 14),
            ]
            for title, status, priority, progress, project_id, assignee_id, due_offset in tasks_seed:
                exists = Task.query.filter_by(title=title).first()
                if exists:
                    continue
                task = Task(
                    title=title,
                    description=f"Seed task for {title}",
                    status=status,
                    priority=priority,
                    progress=progress,
                    project_id=project_id,
                    assignee_id=assignee_id,
                    due_date=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=due_offset),
                )
                db.session.add(task)
            db.session.commit()

        if Document.query.count() < 2:
            docs_seed = [
                ("seed_litigation_brief.pdf", "Litigation_Brief.pdf", DocumentType.PDF, projects[0].id, admin.id),
                ("seed_compliance_notes.docx", "Compliance_Notes.docx", DocumentType.DOCX, projects[1].id, member.id),
            ]
            for filename, original_name, file_type, project_id, uploader_id in docs_seed:
                exists = Document.query.filter_by(original_name=original_name).first()
                if exists:
                    continue
                document = Document(
                    filename=filename,
                    original_name=original_name,
                    file_type=file_type,
                    file_size=1024,
                    extracted_text=f"Seed extracted text for {original_name}.",
                    tags=["seed", "sample"],
                    project_id=project_id,
                    uploaded_by=uploader_id,
                    version=1,
                )
                db.session.add(document)
            db.session.commit()

        session = ChatSession.query.filter_by(title="Seed AI Session", user_id=admin.id).first()
        if not session:
            first_document = Document.query.order_by(Document.id.asc()).first()
            session = ChatSession(
                title="Seed AI Session",
                document_id=first_document.id if first_document else None,
                user_id=admin.id,
            )
            db.session.add(session)
            db.session.commit()

        if len(session.messages) < 2:
            if not session.messages:
                db.session.add(
                    ChatMessage(
                        session_id=session.id,
                        role=ChatMessageRole.USER,
                        content="Can you summarize this document?",
                        citations=[],
                    )
                )
            if len(session.messages) < 2:
                db.session.add(
                    ChatMessage(
                        session_id=session.id,
                        role=ChatMessageRole.ASSISTANT,
                        content="[AI response placeholder – implement with Ollama]",
                        citations=["Document section 1"],
                    )
                )
            db.session.commit()

        print("Seed complete.")


if __name__ == "__main__":
    main()
