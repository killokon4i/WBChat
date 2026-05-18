/**
 * Split-view чатов: список слева, переписка в iframe справа.
 */
(function () {
    function init() {
        const layout = document.getElementById('chatSplitLayout');
        const frame = document.getElementById('chatPanelFrame');
        const empty = document.getElementById('chatPanelEmpty');
        const loading = document.getElementById('chatPanelLoading');
        const mobileBack = document.getElementById('chatMobileBack');
        if (!layout || !frame || !empty) {
            console.warn(
                '[ChatShell] Нет разметки split-view (#chatSplitLayout / #chatPanelFrame / #chatPanelEmpty). Обновите страницу (Ctrl+F5).'
            );
            return;
        }

        let loadToken = 0;
        let currentChatId = frame.dataset.currentChat || '';

        function embedUrl(id) {
            return '/chat/' + id + '/?embed=1';
        }

        function listUrl(id) {
            return id ? '/chat/?c=' + id : '/chat/';
        }

        function showLoading() {
            if (loading) {
                loading.classList.add('is-active');
            }
            frame.classList.add('is-loading');
        }

        function hideLoading() {
            if (loading) {
                loading.classList.remove('is-active');
            }
            frame.classList.remove('is-loading');
        }

        function bindFrameLoad(token, onDone) {
            function finish() {
                if (token !== loadToken) return;
                hideLoading();
                if (typeof onDone === 'function') onDone();
            }

            frame.addEventListener('load', finish, { once: true });

            window.setTimeout(function () {
                if (token === loadToken && frame.classList.contains('is-loading')) {
                    finish();
                }
            }, 20000);
        }

        function setMobileChatMode(active) {
            document.body.classList.toggle('chat-mobile-active', !!active);
        }

        function openChat(id, pushState) {
            if (!id) return;
            id = String(id);
            if (id === currentChatId && frame.classList.contains('is-visible') && !frame.classList.contains('is-loading')) {
                return;
            }

            document.querySelectorAll('.chat-item').forEach(function (el) {
                el.classList.toggle('is-active', el.dataset.conversationId === id);
            });

            currentChatId = id;
            frame.dataset.currentChat = id;
            loadToken += 1;
            const token = loadToken;

            showLoading();
            frame.classList.add('is-visible');
            empty.classList.add('is-hidden');
            layout.classList.add('chat-has-active');
            setMobileChatMode(true);

            bindFrameLoad(token);
            frame.src = embedUrl(id);

            if (pushState !== false) {
                history.pushState({ chatId: id }, '', listUrl(id));
            }
        }

        function removeChatFromList(id) {
            if (!id) return;
            id = String(id);
            document.querySelectorAll('.chat-item').forEach(function (el) {
                if (el.dataset.conversationId === id) {
                    el.remove();
                }
            });
        }

        function getActiveChatId() {
            if (currentChatId) return String(currentChatId);
            var fromFrame = frame.dataset.currentChat;
            if (fromFrame) return String(fromFrame);
            var fromUrl = new URLSearchParams(window.location.search).get('c');
            return fromUrl ? String(fromUrl) : '';
        }

        function closeChat(pushState) {
            loadToken += 1;
            currentChatId = '';
            frame.dataset.currentChat = '';
            hideLoading();
            frame.classList.remove('is-visible', 'is-loading');
            frame.removeAttribute('src');
            frame.src = 'about:blank';
            empty.classList.remove('is-hidden');
            layout.classList.remove('chat-has-active');
            setMobileChatMode(false);
            document.querySelectorAll('.chat-item.is-active').forEach(function (el) {
                el.classList.remove('is-active');
            });
            if (pushState !== false) {
                history.pushState({}, '', listUrl(null));
            }
        }

        function onConversationLeft(id) {
            if (!id) return;
            id = String(id);
            removeChatFromList(id);
            if (getActiveChatId() === id) {
                closeChat();
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

        if (frame.classList.contains('is-visible') && frame.getAttribute('src')) {
            const initialId =
                layout.dataset.initialChat ||
                new URLSearchParams(window.location.search).get('c');
            if (initialId) {
                currentChatId = String(initialId);
                frame.dataset.currentChat = currentChatId;
                loadToken += 1;
                bindFrameLoad(loadToken);
            }
        }

        const initial =
            layout.dataset.initialChat ||
            new URLSearchParams(window.location.search).get('c');
        if (initial && !currentChatId) {
            openChat(initial, false);
        }

        window.ChatShell = {
            openChat: openChat,
            closeChat: closeChat,
            removeChatFromList: removeChatFromList,
            onConversationLeft: onConversationLeft,
            getActiveChatId: getActiveChatId,
        };

        if (window.WBRealtime && typeof window.WBRealtime.syncInbox === 'function') {
            setInterval(window.WBRealtime.syncInbox, 2500);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
