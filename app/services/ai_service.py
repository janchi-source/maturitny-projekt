import re

import ollama
from flask import current_app

_MENTION_RE = re.compile(r'@\[(doc|project|task):\d+:([^\]]+)\]')


def _strip_mentions(text):
    return _MENTION_RE.sub(r'@\2', text)


def _ollama_text(response):
    if isinstance(response, dict):
        return response['message']['content']
    return response.message.content


def _client():
    return ollama.Client(host=current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434'))


def _model():
    return current_app.config.get('OLLAMA_MODEL', 'gemma3:1b')


class AIService:

    def chat(self, session_id, message, context):
        from ..extensions import db
        from ..models.ai_chat import ChatMessage

        system_parts = [
            "You are a helpful AI assistant for ProMat, a project management tool. "
            "Be concise, clear, and professional."
        ]

        doc_id = context.get('document_id')
        if doc_id:
            from ..models.document import Document
            doc = db.session.get(Document, doc_id)
            if doc and doc.extracted_text:
                system_parts.append(
                    f'Session document "{doc.original_name}":\n{doc.extracted_text[:4000]}'
                )

        for mention in context.get('mentions', []):
            block = _load_mention_context(mention)
            if block:
                system_parts.append(block)

        history_rows = (
            ChatMessage.query
            .filter_by(session_id=session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        messages = [{'role': 'system', 'content': '\n\n---\n\n'.join(system_parts)}]
        for row in history_rows[:-1]:
            messages.append({'role': row.role.value, 'content': row.content})
        messages.append({'role': 'user', 'content': _strip_mentions(message)})

        try:
            response = _client().chat(model=_model(), messages=messages, stream=False)
            return _ollama_text(response)
        except Exception as exc:
            current_app.logger.error('Ollama chat error: %s', exc)
            return f'AI unavailable: {exc}'

    def summarize(self, text):
        if not text or not text.strip():
            return 'No text available to summarize.'
        messages = [{'role': 'user', 'content': 'Summarize the following in 3–5 concise sentences:\n\n' + text[:6000]}]
        try:
            response = _client().chat(model=_model(), messages=messages, stream=False)
            return _ollama_text(response)
        except Exception as exc:
            current_app.logger.error('Ollama summarize error: %s', exc)
            return f'AI unavailable: {exc}'


def _load_mention_context(mention):
    from ..extensions import db
    from ..models.document import Document
    from ..models.project import Project
    from ..models.task import Task

    type_slug = mention.get('type')
    entity_id  = mention.get('id')

    # ── Document ──────────────────────────────────────────────────────────
    if type_slug == 'doc':
        doc = db.session.get(Document, entity_id)
        if not doc:
            return None
        lines = [
            f'Document: "{doc.original_name}"',
            f'Type: {doc.file_type.value if doc.file_type else "unknown"}',
            f'Project: {doc.project.name if doc.project else "—"}',
            f'Uploaded by: {doc.uploader.username if doc.uploader else "—"}',
            f'Version: {doc.version}',
        ]
        if doc.tags:
            lines.append(f'Tags: {", ".join(doc.tags)}')
        if doc.extracted_text:
            lines.append(f'\nContent:\n{doc.extracted_text[:4000]}')
        return '\n'.join(lines)

    # ── Project ───────────────────────────────────────────────────────────
    if type_slug == 'project':
        project = db.session.get(Project, entity_id)
        if not project:
            return None
        open_tasks  = [t for t in project.tasks if t.status.value != 'done']
        done_tasks  = [t for t in project.tasks if t.status.value == 'done']
        lines = [
            f'Project: "{project.name}"',
            f'Status: {project.status.value}',
            f'Progress: {project.progress}%',
            f'Owner: {project.owner.username if project.owner else "—"}',
            f'Tasks: {len(project.tasks)} total ({len(open_tasks)} open, {len(done_tasks)} done)',
        ]
        if project.description:
            lines.append(f'Description: {project.description}')
        if open_tasks:
            task_lines = [
                f'  - [{t.status.value}] {t.title} (priority: {t.priority.value})'
                for t in open_tasks[:10]
            ]
            lines.append('Open tasks:\n' + '\n'.join(task_lines))
        return '\n'.join(lines)

    # ── Task ──────────────────────────────────────────────────────────────
    if type_slug == 'task':
        task = db.session.get(Task, entity_id)
        if not task:
            return None
        lines = [
            f'Task: "{task.title}"',
            f'Status: {task.status.value}',
            f'Priority: {task.priority.value}',
            f'Progress: {task.progress}%',
            f'Project: {task.project.name if task.project else "—"}',
        ]
        if task.assignee:
            lines.append(f'Assignee: {task.assignee.username}')
        if task.due_date:
            lines.append(f'Due: {task.due_date.strftime("%Y-%m-%d")}')
        if task.sprint:
            lines.append(f'Sprint: {task.sprint.name}')
        if task.labels:
            lines.append(f'Labels: {", ".join(l.name for l in task.labels)}')
        if task.description:
            lines.append(f'Description: {task.description}')

        # Checklist / to-do items
        if task.checklist_items:
            done  = sum(1 for i in task.checklist_items if i.is_done)
            total = len(task.checklist_items)
            items = '\n'.join(
                f'  [{"x" if i.is_done else " "}] {i.title}'
                for i in task.checklist_items
            )
            lines.append(f'Checklist ({done}/{total} done):\n{items}')

        # Attachments / files
        if task.attachments:
            files = '\n'.join(
                f'  - {a.original_name} ({round(a.file_size / 1024, 1)} KB, v{a.version})'
                for a in task.attachments
            )
            lines.append(f'Attachments:\n{files}')

        # Blocking / blocked-by
        if task.blocking_tasks:
            lines.append(f'Blocked by: {", ".join(t.title for t in task.blocking_tasks)}')
        if task.blocked_tasks:
            lines.append(f'Blocking: {", ".join(t.title for t in task.blocked_tasks)}')

        return '\n'.join(lines)

    return None
