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
    var wsGiveUp = false;
    var maxReconnectAttempts = 4;
    var pollTimer = null;
    var notifyHeartbeatTimer = null;
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
        if (window.WBChatTime) {
            return WBChatTime.formatChatListTime(iso);
        }
        if (!iso) return '';
        var d = new Date(iso);
        if (Number.isNaN(d.getTime())) return '';
        var pad = function (x) { return String(x).padStart(2, '0'); };
        return pad(d.getHours()) + ':' + pad(d.getMinutes());
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

    function startNotificationHeartbeat() {
        if (notifyHeartbeatTimer) return;
        function ping() {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ type: 'heartbeat' }));
            }
        }
        ping();
        notifyHeartbeatTimer = setInterval(ping, 60000);
    }

    function initChatListTimes() {
        if (!window.WBChatTime) return;
        document.querySelectorAll('.chat-item[data-updated-at]').forEach(function (item) {
            var iso = item.getAttribute('data-updated-at');
            var timeEl = item.querySelector('.chat-time');
            if (iso && timeEl) {
                timeEl.textContent = WBChatTime.formatChatListTime(iso);
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
            case 'presence_update':
                try {
                    var chatFrame = document.querySelector('iframe.chat-split-frame');
                    if (chatFrame && chatFrame.contentWindow) {
                        chatFrame.contentWindow.postMessage({
                            source: 'wbchat-parent',
                            type: 'presence_update',
                            user_id: data.user_id,
                            is_online: data.is_online,
                            label: data.label,
                            last_seen_at: data.last_seen_at,
                        }, '*');
                    }
                } catch (err) { /* ignore */ }
                break;
        }
    }

    function connect() {
        if (wsGiveUp) return;
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
            return;
        }
        if (socket) {
            try { socket.onclose = null; socket.close(); } catch (e) { /* ignore */ }
            socket = null;
        }
        var current;
        try {
            current = new WebSocket(wsUrl());
            socket = current;
        } catch (e) {
            scheduleReconnect();
            return;
        }

        current.onopen = function () {
            if (socket !== current) return;
            reconnectAttempt = 0;
            startNotificationHeartbeat();
        };

        current.onmessage = function (e) {
            try {
                handlePayload(JSON.parse(e.data));
            } catch (err) { /* ignore */ }
        };

        current.onclose = function () {
            if (socket !== current) return;
            socket = null;
            scheduleReconnect();
        };

        current.onerror = function () {
            try { current.close(); } catch (err) { /* ignore */ }
        };
    }

    function scheduleReconnect() {
        if (wsGiveUp || reconnectTimer) return;
        reconnectAttempt += 1;
        if (reconnectAttempt >= maxReconnectAttempts) {
            wsGiveUp = true;
            return;
        }
        var delay = Math.min(20000, 2000 * reconnectAttempt);
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

    initChatListTimes();
    startPolling();
    connect();
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
            if (!wsGiveUp) connect();
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
