/**
 * Форматирование времени в стиле мессенджеров (Telegram).
 * window.WBChatTime — для списка чатов и заголовка «был(а) в сети».
 */
(function (global) {
    'use strict';

    var MONTHS_SHORT = [
        '', 'янв.', 'февр.', 'мар.', 'апр.', 'мая', 'июн.',
        'июл.', 'авг.', 'сент.', 'окт.', 'нояб.', 'дек.',
    ];

    var WEEKDAYS = [
        'воскресенье', 'понедельник', 'вторник', 'среда',
        'четверг', 'пятница', 'суббота',
    ];

    function pad2(n) {
        return String(n).padStart(2, '0');
    }

    function parseDate(iso) {
        if (!iso) return null;
        var d = new Date(iso);
        return Number.isNaN(d.getTime()) ? null : d;
    }

    function startOfDay(d) {
        return new Date(d.getFullYear(), d.getMonth(), d.getDate());
    }

    function sameDay(a, b) {
        return (
            a.getFullYear() === b.getFullYear() &&
            a.getMonth() === b.getMonth() &&
            a.getDate() === b.getDate()
        );
    }

    /** Время в пузыре сообщения — всегда ЧЧ:ММ */
    function formatMessageTime(iso) {
        var d = parseDate(iso);
        if (!d) return '';
        return pad2(d.getHours()) + ':' + pad2(d.getMinutes());
    }

    /**
     * Разделитель дня в ленте: Сегодня / Вчера / 15 марта / 15 марта 2024
     */
    function formatDateSeparator(iso) {
        var d = parseDate(iso);
        if (!d) return '';
        var today = new Date();
        var yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        if (sameDay(d, today)) return 'Сегодня';
        if (sameDay(d, yesterday)) return 'Вчера';
        var label = d.getDate() + ' ' + MONTHS_SHORT[d.getMonth() + 1];
        if (d.getFullYear() !== today.getFullYear()) {
            label += ' ' + d.getFullYear();
        }
        return label;
    }

    /**
     * Время в списке чатов: сегодня ЧЧ:ММ → Вчера → Пн → 15 мар. → 15.03.24
     */
    function formatChatListTime(iso) {
        var d = parseDate(iso);
        if (!d) return '';
        var now = new Date();
        var hm = pad2(d.getHours()) + ':' + pad2(d.getMinutes());

        if (sameDay(d, now)) return hm;

        var yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        if (sameDay(d, yesterday)) return 'Вчера';

        var diffDays = Math.floor(
            (startOfDay(now).getTime() - startOfDay(d).getTime()) / 86400000
        );
        if (diffDays > 0 && diffDays < 7) {
            var shortDays = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
            return shortDays[d.getDay()];
        }

        if (d.getFullYear() === now.getFullYear()) {
            return d.getDate() + ' ' + MONTHS_SHORT[d.getMonth() + 1];
        }
        return pad2(d.getDate()) + '.' + pad2(d.getMonth() + 1) + '.' +
            String(d.getFullYear()).slice(-2);
    }

    /**
     * Статус в шапке личного чата (синхрон с сервером при наличии label).
     */
    function formatPresenceLabel(iso, isOnline, serverLabel) {
        if (serverLabel) return serverLabel;
        if (isOnline) return 'в сети';
        var d = parseDate(iso);
        if (!d) return 'не в сети';

        var now = new Date();
        var sec = (now.getTime() - d.getTime()) / 1000;
        var hm = pad2(d.getHours()) + ':' + pad2(d.getMinutes());

        if (sec < 60) return 'был(а) только что';
        if (sec < 3600) {
            var mins = Math.max(1, Math.floor(sec / 60));
            return 'был(а) ' + mins + ' мин. назад';
        }
        if (sameDay(d, now)) return 'был(а) в ' + hm;

        var yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        if (sameDay(d, yesterday)) return 'был(а) вчера в ' + hm;

        var diffDays = Math.floor(
            (startOfDay(now).getTime() - startOfDay(d).getTime()) / 86400000
        );
        if (diffDays > 0 && diffDays < 7) {
            return 'был(а) в ' + WEEKDAYS[d.getDay()] + ' в ' + hm;
        }

        var month = d.getDate() + ' ' + MONTHS_SHORT[d.getMonth() + 1];
        if (d.getFullYear() === now.getFullYear()) {
            return 'был(а) ' + month + ' в ' + hm;
        }
        return 'был(а) ' + pad2(d.getDate()) + '.' + pad2(d.getMonth() + 1) +
            '.' + d.getFullYear();
    }

    function capitalizePresence(label) {
        if (!label) return label;
        return label.charAt(0).toUpperCase() + label.slice(1);
    }

    global.WBChatTime = {
        formatMessageTime: formatMessageTime,
        formatDateSeparator: formatDateSeparator,
        formatChatListTime: formatChatListTime,
        formatPresenceLabel: formatPresenceLabel,
        capitalizePresence: capitalizePresence,
        getMessageDayKey: function (iso) {
            var d = parseDate(iso);
            if (!d) return '';
            return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
        },
    };
})(typeof window !== 'undefined' ? window : this);
