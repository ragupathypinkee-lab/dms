(function () {
    const STATUS_CLASSES = [
        "status-badge-collecting",
        "status-badge-ai_evaluating",
        "status-badge-approving",
        "status-badge-agent_design",
        "status-badge-developing",
        "status-badge-testing",
        "status-badge-launched",
    ];

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta?.content) return meta.content;
        const input = document.querySelector('input[name="csrf_token"]');
        return input?.value || "";
    }

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

        const toastEl = document.createElement("div");
        toastEl.id = id;
        toastEl.className = `toast align-items-center ${bgClass} border-0`;
        toastEl.setAttribute("role", "alert");
        toastEl.setAttribute("aria-live", "assertive");
        toastEl.setAttribute("aria-atomic", "true");

        const wrapper = document.createElement("div");
        wrapper.className = "d-flex";

        const body = document.createElement("div");
        body.className = "toast-body";
        body.textContent = String(message || "");

        const closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "btn-close btn-close-white me-2 m-auto";
        closeBtn.setAttribute("data-bs-dismiss", "toast");

        wrapper.appendChild(body);
        wrapper.appendChild(closeBtn);
        toastEl.appendChild(wrapper);
        container.appendChild(toastEl);

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
        const modalEl = document.getElementById("statusRemarkModal");
        const remarkInput = document.getElementById("statusRemarkInput");
        const remarkSummary = document.getElementById("statusRemarkSummary");
        const remarkCount = document.getElementById("statusRemarkCount");
        const confirmBtn = document.getElementById("statusRemarkConfirm");
        if (!modalEl || !remarkInput || !confirmBtn) return;

        const modal = new bootstrap.Modal(modalEl);
        let pendingChange = null;

        function resetRemarkInput() {
            remarkInput.value = "";
            remarkInput.classList.remove("is-invalid");
            if (remarkCount) remarkCount.textContent = "0";
        }

        function updateRemarkCount() {
            if (remarkCount) remarkCount.textContent = String(remarkInput.value.length);
        }

        remarkInput.addEventListener("input", updateRemarkCount);

        modalEl.addEventListener("hidden.bs.modal", () => {
            pendingChange = null;
            resetRemarkInput();
        });

        async function submitStatusChange() {
            if (!pendingChange) return;

            const remark = remarkInput.value.trim();
            if (!remark) {
                remarkInput.classList.add("is-invalid");
                remarkInput.focus();
                return;
            }

            const { select, form, newStatus } = pendingChange;
            const body = new FormData(form);
            body.set("status", newStatus);
            body.set("remark", remark);

            confirmBtn.disabled = true;
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
                        "X-CSRF-Token": getCsrfToken(),
                    },
                });

                const data = await response.json().catch(() => ({}));
                if (!response.ok || data.ok === false) {
                    throw new Error(data.detail || "update failed");
                }

                select.value = data.status;
                updateStatusSelectClass(select, data.status);
                select.dataset.currentStatus = data.status;
                modal.hide();
                showToast(data.message || "状态更新成功", "success");
            } catch (err) {
                showToast(
                    typeof err.message === "string" && err.message !== "update failed"
                        ? err.message
                        : "状态更新失败，请重试",
                    "danger"
                );
            } finally {
                confirmBtn.disabled = false;
                select.disabled = false;
                select.classList.remove("is-loading");
            }
        }

        confirmBtn.addEventListener("click", submitStatusChange);

        remarkInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                event.preventDefault();
                submitStatusChange();
            }
        });

        document.querySelectorAll(".status-select").forEach((select) => {
            select.dataset.currentStatus = select.value;

            select.addEventListener("change", () => {
                const form = select.closest("form");
                if (!form) return;

                const previous = select.dataset.currentStatus;
                const newStatus = select.value;
                if (previous === newStatus) return;

                const fromLabel =
                    select.querySelector(`option[value="${previous}"]`)?.textContent?.trim() ||
                    previous;
                const toLabel =
                    select.querySelector(`option[value="${newStatus}"]`)?.textContent?.trim() ||
                    newStatus;

                select.value = previous;
                pendingChange = { select, form, previous, newStatus };
                if (remarkSummary) {
                    remarkSummary.textContent = `将状态从「${fromLabel}」变更为「${toLabel}」`;
                }
                resetRemarkInput();
                modal.show();
                setTimeout(() => remarkInput.focus(), 200);
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
            if (label) label.textContent = "评估中...";
            spinner?.classList.remove("d-none");

            try {
                const response = await fetch(url, {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                        "X-Requested-With": "fetch",
                        "X-CSRF-Token": getCsrfToken(),
                    },
                });

                const data = await response.json();
                if (!response.ok || !data.ok) {
                    throw new Error(data.detail || "评估失败");
                }

                if (textarea) textarea.value = data.ai_analysis;
                showToast(
                    data.message || "AI 评估完成",
                    data.is_mock ? "primary" : "success"
                );
            } catch (err) {
                showToast(err.message || "AI 评估失败，请重试", "danger");
            } finally {
                btn.disabled = false;
                if (label) label.textContent = "AI 评估";
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
