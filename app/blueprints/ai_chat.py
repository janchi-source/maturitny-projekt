from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.ai_chat import ChatMessage, ChatMessageRole, ChatSession
from ..models.document import Document
from ..services.ai_service import AIService


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
    selected_session = sessions[0] if sessions else None
    messages = selected_session.messages if selected_session else []
    documents = Document.query.order_by(Document.created_at.desc()).all()

    return render_template(
        "ai_chat/index.html",
        sessions=sessions,
        selected_session=selected_session,
        messages=messages,
        documents=documents,
    )


@ai_chat_bp.route("/sessions", methods=["POST"])
@login_required
def create_session():
    title = request.form.get("title", "").strip() or "New AI Chat"
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
    documents = Document.query.order_by(Document.created_at.desc()).all()

    return render_template(
        "ai_chat/index.html",
        sessions=sessions,
        selected_session=session,
        messages=session.messages,
        documents=documents,
    )


@ai_chat_bp.route("/sessions/<int:session_id>/message", methods=["POST"])
@login_required
def send_message(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    payload = request.get_json(silent=True) or {}
    content = str(payload.get("message", "")).strip()

    if not content:
        return jsonify({"success": False, "error": "Message is required."}), 400

    user_message = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.USER,
        content=content,
        citations=[],
    )
    db.session.add(user_message)
    db.session.commit()

    context = {
        "document_id": session.document_id,
        "user_id": current_user.id,
    }
    assistant_content = ai_service.chat(session.id, content, context)
    assistant_message = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.ASSISTANT,
        content=assistant_content,
        citations=[],
    )
    db.session.add(assistant_message)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "user_message": {
                "id": user_message.id,
                "role": user_message.role.value,
                "content": user_message.content,
                "created_at": user_message.created_at.isoformat(),
            },
            "assistant_message": {
                "id": assistant_message.id,
                "role": assistant_message.role.value,
                "content": assistant_message.content,
                "citations": assistant_message.citations,
                "created_at": assistant_message.created_at.isoformat(),
            },
        }
    )


@ai_chat_bp.route("/summarize/<int:doc_id>", methods=["POST"])
@login_required
def summarize_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    summary = ai_service.summarize(document.extracted_text or "")
    return jsonify({"success": True, "document_id": doc_id, "summary": summary})
