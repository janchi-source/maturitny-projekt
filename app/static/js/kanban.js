function initKanban() {
    const board = document.querySelector("[data-kanban-board]");
    if (!board) {
        return;
    }

    const csrfToken = board.getAttribute("data-csrf-token") || "";
    let draggedCard = null;

    const cards = board.querySelectorAll("[data-task-card]");
    const columns = board.querySelectorAll("[data-kanban-column]");

    cards.forEach((card) => {
        const editToggle = card.querySelector("[data-task-edit-toggle]");
        const cancelButton = card.querySelector("[data-task-edit-cancel]");
        const quickForm = card.querySelector("[data-task-quick-form]");

        card.addEventListener("dragstart", () => {
            if (quickForm && !quickForm.classList.contains("hidden")) {
                return;
            }
            draggedCard = card;
            card.classList.add("opacity-60", "ring-2", "ring-primary");
        });

        card.addEventListener("dragend", () => {
            card.classList.remove("opacity-60", "ring-2", "ring-primary");
            draggedCard = null;
        });

        if (editToggle && quickForm) {
            editToggle.addEventListener("click", () => {
                quickForm.classList.remove("hidden");
                card.setAttribute("draggable", "false");
            });
        }

        if (cancelButton && quickForm) {
            cancelButton.addEventListener("click", () => {
                quickForm.classList.add("hidden");
                card.setAttribute("draggable", "true");
            });
        }

        if (quickForm) {
            quickForm.addEventListener("submit", async (event) => {
                event.preventDefault();

                const formData = new FormData(quickForm);
                const taskId = String(formData.get("task_id") || "");
                if (!taskId) {
                    return;
                }

                const payload = {
                    title: String(formData.get("title") || ""),
                    description: String(formData.get("description") || ""),
                    assignee_id: String(formData.get("assignee_id") || ""),
                    priority: String(formData.get("priority") || ""),
                    status: String(formData.get("status") || ""),
                    due_date: String(formData.get("due_date") || ""),
                    progress: String(formData.get("progress") || "0"),
                };

                const submitButton = quickForm.querySelector("button[type='submit']");
                if (submitButton) {
                    submitButton.disabled = true;
                }

                try {
                    const response = await fetch(`/tasks/${taskId}/quick-update`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": csrfToken,
                        },
                        body: JSON.stringify(payload),
                    });

                    const result = await response.json().catch(() => ({}));
                    if (!response.ok || !result.success) {
                        throw new Error(result.error || "Quick update failed");
                    }

                    const titleNode = card.querySelector("[data-task-title]");
                    const assigneeNode = card.querySelector("[data-task-assignee]");
                    const dueNode = card.querySelector("[data-task-due-display]");

                    if (titleNode) {
                        titleNode.textContent = payload.title || titleNode.textContent;
                    }

                    if (assigneeNode) {
                        const selectedAssignee = quickForm.querySelector("select[name='assignee_id'] option:checked");
                        assigneeNode.textContent = selectedAssignee ? selectedAssignee.textContent : "Unassigned";
                    }

                    if (dueNode) {
                        dueNode.textContent = payload.due_date || "No due date";
                    }

                    const nextStatus = payload.status;
                    const targetColumn = board.querySelector(`[data-kanban-column][data-status='${nextStatus}'] [data-kanban-list]`);
                    if (targetColumn && card.parentElement !== targetColumn) {
                        targetColumn.appendChild(card);
                    }

                    quickForm.classList.add("hidden");
                    card.setAttribute("draggable", "true");
                } catch (error) {
                    window.alert(error.message || "Unable to update task.");
                } finally {
                    if (submitButton) {
                        submitButton.disabled = false;
                    }
                }
            });
        }
    });

    columns.forEach((column) => {
        const list = column.querySelector("[data-kanban-list]");
        if (!list) {
            return;
        }

        column.addEventListener("dragover", (event) => {
            event.preventDefault();
            column.classList.add("ring-2", "ring-primary/50");
        });

        column.addEventListener("dragleave", () => {
            column.classList.remove("ring-2", "ring-primary/50");
        });

        column.addEventListener("drop", async (event) => {
            event.preventDefault();
            column.classList.remove("ring-2", "ring-primary/50");

            if (!draggedCard) {
                return;
            }

            const taskId = draggedCard.getAttribute("data-task-id");
            const nextStatus = column.getAttribute("data-status");
            if (!taskId || !nextStatus) {
                return;
            }

            const previousParent = draggedCard.parentElement;
            list.appendChild(draggedCard);

            try {
                const response = await fetch(`/tasks/${taskId}/status`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ status: nextStatus }),
                });

                if (!response.ok) {
                    throw new Error("Status update failed");
                }
            } catch (error) {
                if (previousParent) {
                    previousParent.appendChild(draggedCard);
                }
            }
        });
    });
}

document.addEventListener("DOMContentLoaded", initKanban);
