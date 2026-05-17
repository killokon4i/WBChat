/**
 * Аватары: инициалы, если нет фото или файл не загрузился.
 */
(function (global) {
    'use strict';

    var TAG = 'div';

    function escapeHtml(text) {
        var d = document.createElement(TAG);
        d.textContent = text == null ? '' : String(text);
        return d.innerHTML;
    }

    function initialsFromName(name) {
        name = (name || '').trim();
        if (!name) return '?';
        var words = name.split(/\s+/);
        if (words.length >= 2) {
            return (words[0][0] + words[words.length - 1][0]).toUpperCase();
        }
        if (name.length >= 2) return name.substring(0, 2).toUpperCase();
        return name[0].toUpperCase();
    }

    function replaceBroken(img) {
        if (!img || !img.parentNode) return;
        var initials = (img.dataset && img.dataset.initials) || '?';
        var span = document.createElement('span');
        span.className = 'avatar-initials';
        span.setAttribute('aria-hidden', 'true');
        span.textContent = initials;
        img.replaceWith(span);
    }

    function slotHtml(opts) {
        opts = opts || {};
        var initials = (opts.initials || '?').toUpperCase();
        var slotClass = opts.slotClass || '';
        var imgClass = opts.imgClass || '';
        var hasAvatar = !!opts.hasAvatar && !!opts.url;
        var open = '<' + TAG + ' class="avatar-slot' + (slotClass ? ' ' + slotClass : '') + '">';
        var close = '</' + TAG + '>';

        if (hasAvatar) {
            return (
                open +
                '<img src="' + escapeHtml(opts.url) + '" alt="" class="' + escapeHtml(imgClass) + '" loading="lazy"' +
                ' data-initials="' + escapeHtml(initials) + '"' +
                ' onerror="window.WBAvatar&&WBAvatar.replaceBroken(this)">' +
                close
            );
        }
        return (
            open +
            '<span class="avatar-initials" aria-hidden="true">' + escapeHtml(initials) + '</span>' +
            close
        );
    }

    global.WBAvatar = {
        initialsFromName: initialsFromName,
        replaceBroken: replaceBroken,
        slotHtml: slotHtml,
    };
})(typeof window !== 'undefined' ? window : global);
