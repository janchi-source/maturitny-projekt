function parseLabels(rawValue) {
    return String(rawValue || "")
        .split(",")
        .map((label) => label.trim())
        .filter((label) => label.length > 0)
        .reduce((unique, label) => {
            if (!unique.some((item) => item.toLowerCase() === label.toLowerCase())) {
                unique.push(label);
            }
            return unique;
        }, []);
}

function initLabelEditor(editor) {
    const hiddenInput = editor.querySelector("[data-label-hidden-input]");
    const chipList = editor.querySelector("[data-label-chip-list]");
    const entryInput = editor.querySelector("[data-label-entry]");
    const addButton = editor.querySelector("[data-label-add]");
    const suggestionButtons = Array.from(editor.querySelectorAll("[data-label-suggest]"));

    if (!hiddenInput || !chipList || !entryInput || !addButton) {
        return;
    }

    let labels = parseLabels(hiddenInput.value);

    const sync = () => {
        hiddenInput.value = labels.join(", ");
        hiddenInput.dispatchEvent(new Event("change", { bubbles: true }));
    };

    const removeLabel = (value) => {
        labels = labels.filter((label) => label.toLowerCase() !== value.toLowerCase());
        render();
        sync();
    };

    const render = () => {
        chipList.innerHTML = "";

        if (!labels.length) {
            const placeholder = document.createElement("span");
            placeholder.className = "text-xs text-slate-500";
            placeholder.textContent = "No labels selected";
            chipList.appendChild(placeholder);
            return;
        }

        labels.forEach((label) => {
            const chip = document.createElement("span");
            chip.className = "inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-100 dark:bg-border-dark text-xs font-semibold";
            chip.textContent = label;

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "text-slate-500 hover:text-red-500";
            removeButton.setAttribute("aria-label", `Remove ${label}`);
            removeButton.textContent = "x";
            removeButton.addEventListener("click", () => removeLabel(label));

            chip.appendChild(removeButton);
            chipList.appendChild(chip);
        });
    };

    const addLabel = (value) => {
        const cleaned = String(value || "").trim();
        if (!cleaned) {
            return;
        }
        if (labels.some((label) => label.toLowerCase() === cleaned.toLowerCase())) {
            entryInput.value = "";
            return;
        }

        labels.push(cleaned);
        entryInput.value = "";
        render();
        sync();
    };

    addButton.addEventListener("click", () => {
        addLabel(entryInput.value);
    });

    entryInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === ",") {
            event.preventDefault();
            addLabel(entryInput.value);
        }
    });

    suggestionButtons.forEach((button) => {
        button.addEventListener("click", () => {
            addLabel(button.getAttribute("data-label-suggest") || "");
        });
    });

    render();
}

document.addEventListener("DOMContentLoaded", () => {
    const editors = document.querySelectorAll("[data-task-label-editor]");
    editors.forEach((editor) => initLabelEditor(editor));
});
