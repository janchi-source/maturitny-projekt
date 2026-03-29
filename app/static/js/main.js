const htmlEl = document.documentElement;

function applyTheme(theme) {
    if (theme === "dark") {
        htmlEl.classList.add("dark");
    } else {
        htmlEl.classList.remove("dark");
    }
}

function initDarkMode() {
    const savedTheme = localStorage.getItem("theme");
    const preferredTheme = savedTheme || "dark";
    applyTheme(preferredTheme);

    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const nextTheme = htmlEl.classList.contains("dark") ? "light" : "dark";
            localStorage.setItem("theme", nextTheme);
            applyTheme(nextTheme);
        });
    });
}

function initSidebar() {
    const sidebar = document.getElementById("app-sidebar");
    const overlay = document.querySelector("[data-sidebar-overlay]");
    const openButtons = document.querySelectorAll("[data-sidebar-open]");
    const closeButtons = document.querySelectorAll("[data-sidebar-close]");

    if (!sidebar || !overlay) {
        return;
    }

    const openSidebar = () => {
        sidebar.classList.remove("-translate-x-full");
        overlay.classList.remove("hidden");
    };

    const closeSidebar = () => {
        sidebar.classList.add("-translate-x-full");
        overlay.classList.add("hidden");
    };

    openButtons.forEach((button) => button.addEventListener("click", openSidebar));
    closeButtons.forEach((button) => button.addEventListener("click", closeSidebar));
    overlay.addEventListener("click", closeSidebar);

    window.addEventListener("resize", () => {
        if (window.innerWidth >= 768) {
            overlay.classList.add("hidden");
            sidebar.classList.remove("-translate-x-full");
        } else {
            sidebar.classList.add("-translate-x-full");
        }
    });
}

function initModals() {
    const openButtons = document.querySelectorAll("[data-modal-target]");
    const closeButtons = document.querySelectorAll("[data-modal-close]");

    const openModal = (modalId) => {
        const modal = document.getElementById(modalId);
        if (!modal) {
            return;
        }
        modal.classList.remove("hidden");
    };

    const closeModal = (modalElement) => {
        const modal = modalElement.closest("[data-modal]");
        if (!modal) {
            return;
        }
        modal.classList.add("hidden");
    };

    openButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const target = button.getAttribute("data-modal-target");
            openModal(target);
        });
    });

    closeButtons.forEach((button) => {
        button.addEventListener("click", () => closeModal(button));
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        document.querySelectorAll("[data-modal]").forEach((modal) => {
            modal.classList.add("hidden");
        });
    });
}

function initNotifications() {
    const toggleButton = document.querySelector("[data-notification-toggle]");
    const menu = document.querySelector("[data-notification-menu]");

    if (!toggleButton || !menu) {
        return;
    }

    toggleButton.addEventListener("click", (event) => {
        event.stopPropagation();
        menu.classList.toggle("hidden");
    });

    document.addEventListener("click", (event) => {
        if (!menu.contains(event.target) && !toggleButton.contains(event.target)) {
            menu.classList.add("hidden");
        }
    });
}

function initProfileMenu() {
    const toggleButton = document.querySelector("[data-profile-toggle]");
    const menu = document.querySelector("[data-profile-menu]");

    if (!toggleButton || !menu) {
        return;
    }

    toggleButton.addEventListener("click", (event) => {
        event.stopPropagation();
        menu.classList.toggle("hidden");
    });

    document.addEventListener("click", (event) => {
        if (!menu.contains(event.target) && !toggleButton.contains(event.target)) {
            menu.classList.add("hidden");
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            menu.classList.add("hidden");
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initDarkMode();
    initSidebar();
    initModals();
    initNotifications();
    initProfileMenu();
});
