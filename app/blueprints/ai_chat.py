import re

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import defer

from ..extensions import db
from ..models.ai_chat import ChatMessage, ChatMessageRole, ChatSession
from ..models.document import Document
from ..models.project import Project
from ..models.task import Task
from ..services.ai_service import AIService

_MENTION_RE = re.compile(r'@\[(doc|project|task):(\d+):([^\]]+)\]')


def _extract_citations(content):
    seen, citations = set(), []
    for m in _MENTION_RE.finditer(content):
        key = (m.group(1), int(m.group(2)))
        if key not in seen:
            seen.add(key)
            citations.append({"type": m.group(1), "id": int(m.group(2)), "label": m.group(3)})
    return citations


ai_chat_bp = Blueprint("ai_chat", __name__)
ai_service = AIService()


@ai_chat_bp.route("/")
@login_required
def index():
    sessions = (
        ChatSession.query.filter_by(user_id=current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    documents = (
        Document.query
        .options(defer(Document.extracted_text))
        .order_by(Document.created_at.desc())
        .all()
    )
    return render_template(
        "ai_chat/index.html",
        sessions=sessions,
        selected_session=None,
        messages=[],
        documents=documents,
    )


@ai_chat_bp.route("/sessions", methods=["POST"])
@login_required
def create_session():
    title = request.form.get("title", "").strip() or "New Chat"
    document_id_raw = request.form.get("document_id", "").strip()
    document_id = int(document_id_raw) if document_id_raw.isdigit() else None

    session = ChatSession(title=title, document_id=document_id, user_id=current_user.id)
    db.session.add(session)
    db.session.commit()

    return redirect(url_for("ai_chat.get_session", session_id=session.id))


@ai_chat_bp.route("/sessions/<int:session_id>")
@login_required
def get_session(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    sessions = (
        ChatSession.query.filter_by(user_id=current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    documents = (
        Document.query
        .options(defer(Document.extracted_text))
        .order_by(Document.created_at.desc())
        .all()
    )
    return render_template(
        "ai_chat/index.html",
        sessions=sessions,
        selected_session=session,
        messages=session.messages,
        documents=documents,
    )


@ai_chat_bp.route("/mentions")
@login_required
def mention_autocomplete():
    q = request.args.get("q", "").strip()
    pattern = f"%{q}%"
    results = []

    docs = (
        Document.query
        .options(defer(Document.extracted_text))
        .filter(Document.original_name.ilike(pattern))
        .order_by(Document.created_at.desc())
        .limit(5)
        .all()
    )
    for d in docs:
        results.append({
            "type": "doc", "id": d.id, "label": d.original_name,
            "meta": d.file_type.value if d.file_type else "",
        })

    projects = (
        Project.query
        .filter(Project.name.ilike(pattern))
        .order_by(Project.updated_at.desc())
        .limit(5)
        .all()
    )
    for p in projects:
        results.append({
            "type": "project", "id": p.id, "label": p.name,
            "meta": p.status.value,
        })

    tasks = (
        Task.query
        .filter(Task.title.ilike(pattern))
        .order_by(Task.created_at.desc())
        .limit(5)
        .all()
    )
    for t in tasks:
        results.append({
            "type": "task", "id": t.id, "label": t.title,
            "meta": t.status.value,
        })

    return jsonify({"results": results})


@ai_chat_bp.route("/sessions/<int:session_id>/message", methods=["POST"])
@login_required
def send_message(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    payload = request.get_json(silent=True) or {}
    content = str(payload.get("message", "")).strip()

    if not content:
        return jsonify({"success": False, "error": "Message is required."}), 400

    citations = _extract_citations(content)

    user_msg = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.USER,
        content=content,
        citations=citations,
    )
    db.session.add(user_msg)
    db.session.commit()

    context = {
        "document_id": session.document_id,
        "user_id": current_user.id,
        "mentions": citations,
    }
    assistant_content = ai_service.chat(session.id, content, context)

    assistant_msg = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.ASSISTANT,
        content=assistant_content,
        citations=citations,
    )
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({
        "success": True,
        "assistant_message": {
            "id": assistant_msg.id,
            "content": assistant_msg.content,
            "citations": assistant_msg.citations,
        },
    })


@ai_chat_bp.route("/sessions/<int:session_id>/delete", methods=["POST"])
@login_required
def delete_session(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    db.session.delete(session)
    db.session.commit()
    return redirect(url_for("ai_chat.index"))


@ai_chat_bp.route("/summarize/<int:doc_id>", methods=["POST"])
@login_required
def summarize_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    summary = ai_service.summarize(document.extracted_text or "")
    return jsonify({"success": True, "document_id": doc_id, "summary": summary})
