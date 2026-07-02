(function () {
    const STATUS_CLASSES = [
        "status-badge-evaluating",
        "status-badge-analyzing",
        "status-badge-developing",
        "status-badge-testing",
        "status-badge-completed",
    ];

    function showToast(message, type) {
        const container = document.getElementById("toastContainer");
        if (!container) return;

        const id = "toast-" + Date.now();
        const bgClass =
            type === "success"
                ? "text-bg-success"
                : type === "danger"
                  ? "text-bg-danger"
                  : "text-bg-primary";

        container.insertAdjacentHTML(
            "beforeend",
            `<div id="${id}" class="toast align-items-center ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>`
        );

        const toastEl = document.getElementById(id);
        const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
        toast.show();
        toastEl.addEventListener("hidden.bs.toast", () => toastEl.remove());
    }

    function updateStatusSelectClass(select, status) {
        STATUS_CLASSES.forEach((cls) => select.classList.remove(cls));
        select.classList.add("status-badge-" + status);
        select.dataset.currentStatus = status;
    }

    function initFlashAlert() {
        const alertEl = document.getElementById("flashAlert");
        if (!alertEl) return;
        setTimeout(() => {
            const alert = bootstrap.Alert.getOrCreateInstance(alertEl);
            alert.close();
        }, 5000);
    }

    function initAutoFilter() {
        document.querySelectorAll("[data-auto-filter]").forEach((select) => {
            select.addEventListener("change", () => {
                const form = select.closest("form");
                if (form) form.submit();
            });
        });
    }

    function initStatusSelects() {
        document.querySelectorAll(".status-select").forEach((select) => {
            select.dataset.currentStatus = select.value;

            select.addEventListener("change", async () => {
                const form = select.closest("form");
                if (!form) return;

                const previous = select.dataset.currentStatus;
                const newStatus = select.value;
                if (previous === newStatus) return;

                const body = new FormData(form);
                select.disabled = true;
                select.classList.add("is-loading");

                try {
                    const response = await fetch(form.action, {
                        method: "POST",
                        body,
                        credentials: "same-origin",
                        headers: {
                            Accept: "application/json",
                            "X-Requested-With": "fetch",
                        },
                    });

                    const data = await response.json().catch(() => ({}));
                    if (!response.ok || data.ok === false) {
                        throw new Error(data.detail || "update failed");
                    }

                    updateStatusSelectClass(select, data.status);
                    select.dataset.currentStatus = data.status;
                    showToast(data.message || "状态更新成功", "success");
                } catch (err) {
                    select.value = previous;
                    showToast(
                        typeof err.message === "string" && err.message !== "update failed"
                            ? err.message
                            : "状态更新失败，请重试",
                        "danger"
                    );
                } finally {
                    select.disabled = false;
                    select.classList.remove("is-loading");
                }
            });
        });
    }

    function initAiAnalyze() {
        const btn = document.getElementById("btnAiAnalyze");
        if (!btn) return;

        const url = btn.dataset.analyzeUrl;
        const textarea = document.getElementById("ai_analysis");
        const label = btn.querySelector(".btn-ai-label");
        const spinner = btn.querySelector(".spinner-border");

        btn.addEventListener("click", async () => {
            btn.disabled = true;
            if (label) label.textContent = "分析中...";
            spinner?.classList.remove("d-none");

            try {
                const response = await fetch(url, {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                        "X-Requested-With": "fetch",
                    },
                });

                const data = await response.json();
                if (!response.ok || !data.ok) {
                    throw new Error(data.detail || "分析失败");
                }

                if (textarea) textarea.value = data.ai_analysis;
                showToast(
                    data.message || "AI 分析完成",
                    data.is_mock ? "primary" : "success"
                );
            } catch (err) {
                showToast(err.message || "AI 分析失败，请重试", "danger");
            } finally {
                btn.disabled = false;
                if (label) label.textContent = "AI 分析";
                spinner?.classList.add("d-none");
            }
        });
    }

    function initFormValidation() {
        document.querySelectorAll(".needs-validation").forEach((form) => {
            form.addEventListener(
                "submit",
                (event) => {
                    if (!form.checkValidity()) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                    form.classList.add("was-validated");
                },
                false
            );
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        initFlashAlert();
        initAutoFilter();
        initStatusSelects();
        initFormValidation();
        initAiAnalyze();
    });
})();
