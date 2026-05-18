/**
 * Звук и системные уведомления о новых сообщениях (вне активного чата / вкладки).
 */
(function (global) {
    'use strict';

    var SOUND_URLS = ['/static/sounds/message.mp3', '/static/sounds/message.wav'];
    var permissionAsked = false;
    var currentUserId = null;

    function getActiveChatId() {
        if (global.__wbActiveChatId != null) {
            return parseInt(global.__wbActiveChatId, 10) || null;
        }
        try {
            var m = location.search.match(/[?&]c=(\d+)/);
            if (m) return parseInt(m[1], 10);
        } catch (e) { /* ignore */ }
        return null;
    }

    function isOnChatPage() {
        return /\/chat\/?/i.test(location.pathname);
    }

    function shouldNotify(data) {
        if (!data || data.type !== 'chat_inbox') return false;
        if (data.sender_id != null && currentUserId != null && data.sender_id === currentUserId) {
            return false;
        }
        var convId = parseInt(data.conversation_id, 10);
        var activeId = getActiveChatId();
        var pageVisible = document.visibilityState === 'visible';
        var hasFocus = typeof document.hasFocus === 'function' ? document.hasFocus() : pageVisible;

        if (pageVisible && hasFocus && isOnChatPage() && activeId && convId === activeId) {
            return false;
        }
        return true;
    }

    function playUrl(index) {
        if (index >= SOUND_URLS.length) {
            playBeepFallback();
            return;
        }
        var a = new Audio(SOUND_URLS[index]);
        a.preload = 'auto';
        var p = a.play();
        if (p && typeof p.catch === 'function') {
            p.catch(function () {
                playUrl(index + 1);
            });
        }
    }

    function playBeepFallback() {
        try {
            var Ctx = global.AudioContext || global.webkitAudioContext;
            if (!Ctx) return;
            var ctx = new Ctx();
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = 880;
            gain.gain.value = 0.08;
            osc.start();
            osc.stop(ctx.currentTime + 0.12);
            setTimeout(function () { ctx.close(); }, 200);
        } catch (e) { /* ignore */ }
    }

    function playMessageSound() {
        playUrl(0);
    }

    function requestPermissionOnce() {
        if (permissionAsked || !('Notification' in global)) return;
        if (Notification.permission === 'granted' || Notification.permission === 'denied') {
            permissionAsked = true;
            return;
        }
        permissionAsked = true;
        try {
            Notification.requestPermission();
        } catch (e) { /* ignore */ }
    }

    function notificationBody(data) {
        var preview = data.preview || 'Новое сообщение';
        if (data.author_name && preview.indexOf(data.author_name) !== 0) {
            return data.author_name + ': ' + preview;
        }
        return preview;
    }

    function showBrowserNotification(data) {
        if (!('Notification' in global) || Notification.permission !== 'granted') {
            return;
        }
        var title = data.conversation_name || 'WB Хаб — новое сообщение';
        var body = notificationBody(data);
        var icon = '/static/img/favicon.svg';
        var n;
        try {
            n = new Notification(title, {
                body: body,
                icon: icon,
                tag: 'wbchat-' + (data.conversation_id || '0'),
                renotify: true,
            });
        } catch (e) {
            return;
        }
        n.onclick = function () {
            try { global.focus(); } catch (err) { /* ignore */ }
            var url = '/chat/?c=' + encodeURIComponent(data.conversation_id || '');
            if (location.pathname.indexOf('/chat') === -1) {
                location.href = url;
            } else {
                location.search = '?c=' + encodeURIComponent(data.conversation_id || '');
            }
            n.close();
        };
        setTimeout(function () { n.close(); }, 8000);
    }

    function handleChatInbox(data) {
        if (!shouldNotify(data)) return;
        playMessageSound();
        showBrowserNotification(data);
    }

    function install() {
        document.body.addEventListener('click', requestPermissionOnce, { once: true, capture: true });
        document.body.addEventListener('keydown', requestPermissionOnce, { once: true, capture: true });

        global.addEventListener('message', function (ev) {
            var d = ev.data;
            if (!d) return;
            if (d.source === 'wbchat-embed' && d.type === 'chat_active') {
                global.__wbActiveChatId = d.conversation_id;
            }
        });

    }

    global.WBChatNotify = {
        init: function (opts) {
            currentUserId = opts && opts.userId != null ? parseInt(opts.userId, 10) : null;
            install();
        },
        handleChatInbox: handleChatInbox,
        playMessageSound: playMessageSound,
        requestPermission: requestPermissionOnce,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', install);
    } else {
        install();
    }
})(window);
