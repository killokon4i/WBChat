/**
 * Global WebSocket + polling: notifications, chat list, badges.
 */
(function () {
    if (!document.body || !document.body.classList.contains('portal-body')) {
        return;
    }

    var socket = null;
    var reconnectTimer = null;
    var reconnectAttempt = 0;
    var pollTimer = null;
    var POLL_MS = 2500;

    function wsUrl() {
        var scheme = location.protocol === 'https:' ? 'wss://' : 'ws://';
        return scheme + location.host + '/ws/notifications/';
    }

    function setBadge(name, count) {
        var n = parseInt(count, 10) || 0;
        document.querySelectorAll('[data-wb-badge="' + name + '"]').forEach(function (el) {
            if (n > 0) {
                el.textContent = n > 99 ? '99+' : String(n);
                el.style.display = '';
                el.hidden = false;
            } else {
                el.textContent = '';
                el.style.display = 'none';
                el.hidden = true;
            }
        });
    }

    function applyCounts(counts) {
        if (!counts) return;
        setBadge('notifications', counts.notifications_unread);
        setBadge('chats', counts.messages_unread);
        if (counts.conversations) {
            counts.conversations.forEach(function (c) {
                updateChatListItem(c.id, { unread_count: c.unread_count }, false);
            });
        }
    }

    function formatChatTime(iso) {
        if (!iso) return '';
        var d = new Date(iso);
        if (Number.isNaN(d.getTime())) return '';
        var now = new Date();
        var pad = function (x) { return String(x).padStart(2, '0'); };
        if (d.toDateString() === now.toDateString()) {
            return pad(d.getHours()) + ':' + pad(d.getMinutes());
        }
        return pad(d.getDate()) + '.' + pad(d.getMonth() + 1) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }

    function updateChatListItem(conversationId, data, moveToTop) {
        var item = document.querySelector('.chat-item[data-conversation-id="' + conversationId + '"]');
        if (!item) return;

        var previewEl = item.querySelector('.chat-last-message');
        if (data.preview && previewEl) {
            var badge = previewEl.querySelector('.chat-type-badge');
            var badgeHtml = badge ? badge.outerHTML : '';
            previewEl.innerHTML = badgeHtml + ' <span class="chat-preview-text">' + escapeHtml(data.preview) + '</span>';
        }

        if (data.updated_at) {
            var timeEl = item.querySelector('.chat-time');
            if (timeEl) timeEl.textContent = formatChatTime(data.updated_at);
            item.dataset.updatedAt = data.updated_at;
        }

        if (data.unread_count !== undefined && data.unread_count !== null) {
            var unread = parseInt(data.unread_count, 10) || 0;
            var previewWrap = item.querySelector('.chat-preview');
            if (previewWrap) {
                var unreadEl = previewWrap.querySelector('.chat-unread');
                if (unread > 0) {
                    if (!unreadEl) {
                        unreadEl = document.createElement('span');
                        unreadEl.className = 'chat-unread';
                        previewWrap.appendChild(unreadEl);
                    }
                    unreadEl.textContent = unread > 99 ? '99+' : String(unread);
                } else if (unreadEl) {
                    unreadEl.remove();
                }
            }
        }

        if (moveToTop) {
            var list = item.closest('.chat-list');
            if (list && item.parentNode === list) {
                list.prepend(item);
            }
        }
    }

    /** API отдаёт чаты от новых к старым; appendChild по порядку = новые сверху */
    function reorderChatList(conversations) {
        var list = document.querySelector('.chat-list');
        if (!list || !conversations || !conversations.length) return;
        conversations.forEach(function (c) {
            var item = document.querySelector('.chat-item[data-conversation-id="' + c.id + '"]');
            if (item && item.parentNode === list) {
                list.appendChild(item);
            }
        });
    }

    function escapeHtml(text) {
        var d = document.createElement('div');
        d.textContent = text == null ? '' : String(text);
        return d.innerHTML;
    }

    function syncInboxFromServer() {
        if (!document.querySelector('.chat-split-layout') && !document.querySelector('[data-wb-badge="chats"]')) {
            return;
        }
        fetch('/chat/api/inbox-sync/', {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' },
        })
            .then(function (r) {
                if (!r.ok) throw new Error('sync');
                return r.json();
            })
            .then(function (data) {
                if (!data.success) return;
                if (data.counts) applyCounts(data.counts);
                var convs = data.conversations || [];
                convs.forEach(function (c) {
                    updateChatListItem(c.id, {
                        unread_count: c.unread_count,
                        preview: c.preview,
                        updated_at: c.updated_at,
                    }, false);
                });
                reorderChatList(convs);
            })
            .catch(function () { /* silent */ });
    }

    function startPolling() {
        if (pollTimer) return;
        syncInboxFromServer();
        pollTimer = setInterval(syncInboxFromServer, POLL_MS);
    }

    function handlePayload(data) {
        if (!data || !data.type) return;

        if (data.counts) {
            applyCounts(data.counts);
        }

        switch (data.type) {
            case 'counts_update':
                break;
            case 'notification':
                break;
            case 'chat_inbox':
                updateChatListItem(data.conversation_id, {
                    unread_count: data.unread_count,
                    preview: data.author_name
                        ? data.author_name + ': ' + (data.preview || '')
                        : data.preview,
                    updated_at: data.updated_at,
                }, true);
                break;
            case 'chat_read':
                updateChatListItem(data.conversation_id, { unread_count: 0 }, false);
                break;
        }
    }

    function connect() {
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
            return;
        }
        try {
            socket = new WebSocket(wsUrl());
        } catch (e) {
            scheduleReconnect();
            return;
        }

        socket.onopen = function () {
            reconnectAttempt = 0;
        };

        socket.onmessage = function (e) {
            try {
                handlePayload(JSON.parse(e.data));
            } catch (err) { /* ignore */ }
        };

        socket.onclose = function () {
            scheduleReconnect();
        };

        socket.onerror = function () {
            try { socket.close(); } catch (err) { /* ignore */ }
        };
    }

    function scheduleReconnect() {
        if (reconnectTimer) return;
        reconnectAttempt += 1;
        var delay = Math.min(30000, 2000 * reconnectAttempt);
        reconnectTimer = setTimeout(function () {
            reconnectTimer = null;
            connect();
        }, delay);
    }

    window.addEventListener('message', function (ev) {
        var d = ev.data;
        if (!d || d.source !== 'wbchat-embed') return;
        if (d.type === 'chat_inbox') {
            updateChatListItem(d.conversation_id, {
                unread_count: d.unread_count,
                preview: d.preview,
                updated_at: d.updated_at,
            }, true);
            if (d.counts) applyCounts(d.counts);
        }
        if (d.type === 'chat_read') {
            updateChatListItem(d.conversation_id, { unread_count: 0 }, false);
        }
    });

    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-mark-read]');
        if (!btn) return;
        var id = btn.getAttribute('data-mark-read');
        if (!id) return;
        e.preventDefault();
        fetch('/notifications/' + id + '/read/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
        }).then(function (r) {
            if (!r.ok) return;
            var card = document.querySelector('.notification-card[data-id="' + id + '"]');
            if (card) {
                card.classList.remove('unread');
                btn.remove();
            }
        });
    });

    function getCsrfToken() {
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : '';
    }

    startPolling();
    connect();
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
            connect();
            syncInboxFromServer();
        }
    });

    window.WBRealtime = {
        connect: connect,
        applyCounts: applyCounts,
        updateChatListItem: updateChatListItem,
        syncInbox: syncInboxFromServer,
    };
})();
