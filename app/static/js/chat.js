function appendMessage(container, role, content, citations = []) {
    const wrapper = document.createElement("div");
    wrapper.className = role === "user" ? "flex justify-end" : "flex justify-start";

    const bubble = document.createElement("div");
    if (role === "user") {
        bubble.className = "max-w-[80%] rounded-xl px-4 py-3 bg-primary text-white text-sm";
    } else {
        bubble.className = "max-w-[85%] rounded-xl px-4 py-3 bg-slate-100 dark:bg-border-dark text-sm";
    }

    const text = document.createElement("p");
    text.textContent = content;
    bubble.appendChild(text);

    if (role !== "user" && Array.isArray(citations) && citations.length > 0) {
        const citationWrap = document.createElement("div");
        citationWrap.className = "mt-2 flex flex-wrap gap-1";
        citations.forEach((citation) => {
            const chip = document.createElement("span");
            chip.className = "text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary font-bold";
            chip.textContent = citation;
            citationWrap.appendChild(chip);
        });
        bubble.appendChild(citationWrap);
    }

    wrapper.appendChild(bubble);
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

function initChat() {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const messages = document.getElementById("chat-messages");
    const csrfToken = document.getElementById("chat-csrf")?.value || "";

    if (!form || !input || !messages) {
        return;
    }

    messages.scrollTop = messages.scrollHeight;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const sendUrl = form.getAttribute("data-send-url");
        const message = input.value.trim();
        if (!sendUrl || !message) {
            return;
        }

        appendMessage(messages, "user", message);
        input.value = "";

        const typing = document.createElement("div");
        typing.className = "flex justify-start";
        typing.innerHTML = '<div class="max-w-[85%] rounded-xl px-4 py-3 bg-slate-100 dark:bg-border-dark text-sm text-slate-500">AI is typing...</div>';
        messages.appendChild(typing);
        messages.scrollTop = messages.scrollHeight;

        try {
            const response = await fetch(sendUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({ message }),
            });
            const payload = await response.json();
            typing.remove();

            if (!response.ok || !payload.success) {
                appendMessage(messages, "assistant", payload.error || "Failed to send message.");
                return;
            }

            appendMessage(
                messages,
                "assistant",
                payload.assistant_message.content,
                payload.assistant_message.citations || []
            );
        } catch (error) {
            typing.remove();
            appendMessage(messages, "assistant", "Network error while contacting AI endpoint.");
        }
    });

    document.querySelectorAll("[data-summarize-btn]").forEach((button) => {
        button.addEventListener("click", async () => {
            const docId = button.getAttribute("data-doc-id");
            if (!docId) {
                return;
            }

            button.disabled = true;
            try {
                const response = await fetch(`/ai-chat/summarize/${docId}`, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                    },
                });
                const payload = await response.json();
                if (response.ok && payload.success) {
                    appendMessage(messages, "assistant", payload.summary);
                }
            } finally {
                button.disabled = false;
            }
        });
    });
}

document.addEventListener("DOMContentLoaded", initChat);
