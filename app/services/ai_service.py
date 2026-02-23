class AIService:
    """Service wrapper for AI features.

    The project owner will replace placeholder responses with Ollama-powered logic.
    """

    def chat(self, session_id, message, context):
        """Return an assistant response for a chat message.

        Args:
            session_id: ChatSession primary key.
            message: User message string.
            context: Optional structured context (documents/session metadata).

        Returns:
            Placeholder assistant response string.
        """
        return "[AI response placeholder – implement with Ollama]"

    def summarize(self, text):
        """Return a short summary for a source text.

        Args:
            text: Raw document text to summarize.

        Returns:
            Placeholder summary string.
        """
        return "[AI summary placeholder – implement with Ollama]"

    def search_terms(self, query, documents):
        """Return semantic matches for a query across documents.

        Args:
            query: Search query string.
            documents: Iterable of document-like objects.

        Returns:
            Placeholder list of semantic matches.
        """
        return ["[AI search placeholder – implement with Ollama]"]
