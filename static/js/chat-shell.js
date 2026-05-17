/**
 * Split-view чатов: список слева, переписка в iframe справа.
 */
(function () {
    function init() {
        const layout = document.getElementById('chatSplitLayout');
        const frame = document.getElementById('chatPanelFrame');
        const empty = document.getElementById('chatPanelEmpty');
        const mobileBack = document.getElementById('chatMobileBack');
        if (!layout || !frame || !empty) {
            console.warn(
                '[ChatShell] Нет разметки split-view (#chatSplitLayout / #chatPanelFrame / #chatPanelEmpty). Обновите страницу (Ctrl+F5).'
            );
            return;
        }

        function embedUrl(id) {
            return '/chat/' + id + '/?embed=1';
        }

        function listUrl(id) {
            return id ? '/chat/?c=' + id : '/chat/';
        }

        function openChat(id, pushState) {
            if (!id) return;
            id = String(id);
            document.querySelectorAll('.chat-item').forEach(function (el) {
                el.classList.toggle('is-active', el.dataset.conversationId === id);
            });
            frame.src = embedUrl(id);
            frame.classList.add('is-visible');
            empty.classList.add('is-hidden');
            layout.classList.add('chat-has-active');
            if (pushState !== false) {
                history.pushState({ chatId: id }, '', listUrl(id));
            }
        }

        function closeChat(pushState) {
            frame.classList.remove('is-visible');
            frame.removeAttribute('src');
            frame.src = 'about:blank';
            empty.classList.remove('is-hidden');
            layout.classList.remove('chat-has-active');
            document.querySelectorAll('.chat-item.is-active').forEach(function (el) {
                el.classList.remove('is-active');
            });
            if (pushState !== false) {
                history.pushState({}, '', listUrl(null));
            }
        }

        document.querySelectorAll('.chat-item').forEach(function (el) {
            el.addEventListener('click', function (e) {
                if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
                e.preventDefault();
                openChat(el.dataset.conversationId);
            });
        });

        if (mobileBack) {
            mobileBack.addEventListener('click', function () {
                closeChat();
            });
        }

        window.addEventListener('popstate', function () {
            const id = new URLSearchParams(window.location.search).get('c');
            if (id) {
                openChat(id, false);
            } else {
                closeChat(false);
            }
        });

        const initial =
            layout.dataset.initialChat ||
            new URLSearchParams(window.location.search).get('c');
        if (initial) {
            openChat(initial, false);
        }

        window.ChatShell = { openChat: openChat, closeChat: closeChat };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
