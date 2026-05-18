(function (global) {
    'use strict';

    var overlay = null;

    function ensureOverlay() {
        if (overlay) return overlay;

        overlay = document.createElement("div");
        overlay.id = "wb-confirm-overlay";
        overlay.className = "wb-confirm-overlay";
        overlay.setAttribute("role", "presentation");
        overlay.innerHTML =
            '<div class="wb-confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="wb-confirm-title">' +
            '<div class="wb-confirm-icon" id="wb-confirm-icon" aria-hidden="true">' +
            '<svg viewBox="0 0 24 24"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14z"></path>' +
            '<line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>' +
            '</div>' +
            '<h2 class="wb-confirm-title" id="wb-confirm-title"></h2>' +
            '<p class="wb-confirm-message" id="wb-confirm-message"></p>' +
            '<div class="wb-confirm-actions">' +
            '<button type="button" class="wb-confirm-btn wb-confirm-btn-cancel" id="wb-confirm-cancel">Отмена</button>' +
            '<button type="button" class="wb-confirm-btn wb-confirm-btn-primary" id="wb-confirm-ok">Подтвердить</button>' +
            '</div></div>';

        document.body.appendChild(overlay);
        return overlay;
    }

    function showConfirm(options) {
        options = options || {};
        var title = options.title || "Подтвердите действие";
        var message = options.message || "";
        var confirmText = options.confirmText || "Подтвердить";
        var cancelText = options.cancelText || "Отмена";
        var danger = !!options.danger;

        return new Promise(function (resolve) {
            var root = ensureOverlay();
            var icon = root.querySelector("#wb-confirm-icon");
            var titleEl = root.querySelector("#wb-confirm-title");
            var messageEl = root.querySelector("#wb-confirm-message");
            var okBtn = root.querySelector("#wb-confirm-ok");
            var cancelBtn = root.querySelector("#wb-confirm-cancel");

            titleEl.textContent = title;
            messageEl.textContent = message;
            messageEl.hidden = !message;
            okBtn.textContent = confirmText;
            cancelBtn.textContent = cancelText;
            okBtn.className = "wb-confirm-btn " + (danger ? "wb-confirm-btn-danger" : "wb-confirm-btn-primary");
            icon.classList.toggle("is-danger", danger);

            function finish(value) {
                root.classList.remove("active");
                okBtn.removeEventListener("click", onOk);
                cancelBtn.removeEventListener("click", onCancel);
                root.removeEventListener("click", onBackdrop);
                document.removeEventListener("keydown", onKey);
                resolve(!!value);
            }

            function onOk(e) {
                e.stopPropagation();
                finish(true);
            }

            function onCancel(e) {
                e.stopPropagation();
                finish(false);
            }

            function onBackdrop(e) {
                if (e.target === root) finish(false);
            }

            function onKey(e) {
                if (e.key === "Escape") finish(false);
            }

            okBtn.addEventListener("click", onOk);
            cancelBtn.addEventListener("click", onCancel);
            root.addEventListener("click", onBackdrop);
            document.addEventListener("keydown", onKey);
            root.classList.add("active");
            requestAnimationFrame(function () {
                cancelBtn.focus();
            });
        });
    }

    global.showConfirm = showConfirm;
})(typeof window !== "undefined" ? window : this);
