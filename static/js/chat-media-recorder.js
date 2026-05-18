/**
 * Голосовые сообщения и видео-кружки (Telegram-style) для чата WB Hub.
 */
(function (global) {
    'use strict';

    var VOICE_MAX_SEC = 300;
    var VNOTE_MAX_SEC = 60;
    var VNOTE_SIZE = 480;

    var state = {
        conversationId: null,
        csrfToken: '',
        uploadFn: null,
        showToast: function () {},
        onLockInput: function () {},
        replyToId: null,
        getReplyToId: function () { return null; },
    };

    var voiceRec = null;
    var voiceChunks = [];
    var voiceStartedAt = 0;
    var voiceStream = null;
    var voiceActive = false;

    var vnoteStream = null;
    var vnoteRecorder = null;
    var vnoteChunks = [];
    var vnoteRaf = null;
    var vnoteStartedAt = 0;
    var vnoteActive = false;

    function pickMime(candidates) {
        if (!global.MediaRecorder || !MediaRecorder.isTypeSupported) return '';
        for (var i = 0; i < candidates.length; i++) {
            if (MediaRecorder.isTypeSupported(candidates[i])) return candidates[i];
        }
        return '';
    }

    function extForMime(mime) {
        if (!mime) return '.webm';
        if (mime.indexOf('mp4') !== -1) return '.mp4';
        if (mime.indexOf('ogg') !== -1) return '.ogg';
        return '.webm';
    }

    function formatDuration(sec) {
        sec = Math.max(0, Math.floor(sec || 0));
        var m = Math.floor(sec / 60);
        var s = sec % 60;
        return m + ':' + String(s).padStart(2, '0');
    }

    function stopStream(stream) {
        if (!stream) return;
        stream.getTracks().forEach(function (t) { t.stop(); });
    }

    function setVoiceUi(active, sec) {
        var btn = document.getElementById('chat-voice-btn');
        var panel = document.getElementById('voice-record-panel');
        var timer = document.getElementById('voice-record-timer');
        if (btn) btn.classList.toggle('is-recording', !!active);
        if (panel) panel.classList.toggle('active', !!active);
        if (timer && sec != null) timer.textContent = formatDuration(sec);
    }

    function setVnoteUi(active, sec) {
        var overlay = document.getElementById('vnote-overlay');
        var timer = document.getElementById('vnote-timer');
        var recBtn = document.getElementById('vnote-record-btn');
        if (overlay) overlay.classList.toggle('is-recording', !!active);
        if (recBtn) recBtn.classList.toggle('is-recording', !!active);
        if (timer && sec != null) timer.textContent = formatDuration(sec);
    }

    function uploadBlob(blob, filename, variant, durationSec) {
        if (!state.uploadFn) return Promise.reject(new Error('no_upload'));
        var fd = new FormData();
        fd.append('files', blob, filename);
        fd.append('variant', variant);
        if (durationSec != null) fd.append('duration', String(durationSec));
        var reply = state.getReplyToId ? state.getReplyToId() : state.replyToId;
        if (reply) fd.append('reply_to', String(reply));
        state.onLockInput(true);
        return state.uploadFn(fd).finally(function () {
            state.onLockInput(false);
        });
    }

  /* ---------- Voice ---------- */

    function stopVoiceTimer() {
        if (voiceRec && voiceRec._timer) {
            clearInterval(voiceRec._timer);
            voiceRec._timer = null;
        }
    }

    function cancelVoice() {
        stopVoiceTimer();
        voiceActive = false;
        if (voiceRec && voiceRec.state !== 'inactive') {
            try { voiceRec.stop(); } catch (e) { /* ignore */ }
        }
        voiceRec = null;
        voiceChunks = [];
        stopStream(voiceStream);
        voiceStream = null;
        setVoiceUi(false);
    }

    function finishVoice(blob, mime, durationSec) {
        var name = 'voice_' + Date.now() + extForMime(mime);
        return uploadBlob(blob, name, 'voice', durationSec);
    }

    function startVoice() {
        if (voiceActive || vnoteActive) return;
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            state.showToast('Микрофон недоступен в этом браузере');
            return;
        }
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                voiceStream = stream;
                voiceChunks = [];
                var mime = pickMime([
                    'audio/webm;codecs=opus',
                    'audio/webm',
                    'audio/ogg;codecs=opus',
                    'audio/mp4',
                ]);
                try {
                    voiceRec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
                } catch (e) {
                    voiceRec = new MediaRecorder(stream);
                }
                mime = voiceRec.mimeType || mime;
                voiceRec.ondataavailable = function (e) {
                    if (e.data && e.data.size) voiceChunks.push(e.data);
                };
                voiceRec.onstop = function () {
                    var dur = Math.round((Date.now() - voiceStartedAt) / 1000);
                    stopStream(voiceStream);
                    voiceStream = null;
                    voiceActive = false;
                    setVoiceUi(false);
                    var blob = new Blob(voiceChunks, { type: mime || 'audio/webm' });
                    voiceChunks = [];
                    if (!blob.size || dur < 1) {
                        state.showToast('Запись слишком короткая');
                        return;
                    }
                    finishVoice(blob, mime, dur)
                        .catch(function (err) {
                            var msg = err && err.error ? err.error : 'Не удалось отправить голосовое';
                            state.showToast(msg);
                        });
                };
                voiceRec.onerror = function () {
                    cancelVoice();
                    state.showToast('Ошибка записи');
                };
                voiceStartedAt = Date.now();
                voiceActive = true;
                voiceRec.start(250);
                setVoiceUi(true, 0);
                voiceRec._timer = setInterval(function () {
                    var sec = (Date.now() - voiceStartedAt) / 1000;
                    setVoiceUi(true, sec);
                    if (sec >= VOICE_MAX_SEC) stopVoice();
                }, 200);
            })
            .catch(function () {
                state.showToast('Нет доступа к микрофону');
            });
    }

    function stopVoice() {
        if (!voiceActive || !voiceRec) return;
        stopVoiceTimer();
        try {
            if (voiceRec.state === 'recording') voiceRec.stop();
        } catch (e) {
            cancelVoice();
        }
    }

    function toggleVoice() {
        if (voiceActive) stopVoice();
        else startVoice();
    }

  /* ---------- Video note ---------- */

    var vnoteCanvas = null;
    var vnoteVideo = null;

    function drawVnoteFrame() {
        if (!vnoteCanvas || !vnoteVideo || vnoteVideo.readyState < 2) return;
        var ctx = vnoteCanvas.getContext('2d');
        var w = vnoteCanvas.width;
        var h = vnoteCanvas.height;
        var vw = vnoteVideo.videoWidth;
        var vh = vnoteVideo.videoHeight;
        if (!vw || !vh) return;
        var side = Math.min(vw, vh);
        var sx = (vw - side) / 2;
        var sy = (vh - side) / 2;
        ctx.clearRect(0, 0, w, h);
        ctx.save();
        ctx.beginPath();
        ctx.arc(w / 2, h / 2, w / 2, 0, Math.PI * 2);
        ctx.closePath();
        ctx.clip();
        ctx.drawImage(vnoteVideo, sx, sy, side, side, 0, 0, w, h);
        ctx.restore();
    }

    function vnoteLoop() {
        drawVnoteFrame();
        vnoteRaf = requestAnimationFrame(vnoteLoop);
    }

    function openVnoteOverlay() {
        var overlay = document.getElementById('vnote-overlay');
        if (overlay) overlay.classList.add('active');
        setVnoteUi(false, 0);
    }

    function closeVnoteOverlay() {
        cancelVnote();
        var overlay = document.getElementById('vnote-overlay');
        if (overlay) overlay.classList.remove('active');
    }

    function cancelVnote() {
        if (vnoteRec && vnoteRec._timer) {
            clearInterval(vnoteRec._timer);
            vnoteRec._timer = null;
        }
        if (vnoteRaf) {
            cancelAnimationFrame(vnoteRaf);
            vnoteRaf = null;
        }
        vnoteActive = false;
        if (vnoteRecorder && vnoteRecorder.state !== 'inactive') {
            try { vnoteRecorder.stop(); } catch (e) { /* ignore */ }
        }
        vnoteRecorder = null;
        vnoteChunks = [];
        stopStream(vnoteStream);
        vnoteStream = null;
        setVnoteUi(false);
    }

    function prepareVnotePreview() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            state.showToast('Камера недоступна');
            return Promise.reject();
        }
        return navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 720 }, height: { ideal: 720 } },
            audio: true,
        }).then(function (stream) {
            vnoteStream = stream;
            vnoteVideo = document.getElementById('vnote-preview-video');
            vnoteCanvas = document.getElementById('vnote-preview-canvas');
            if (!vnoteVideo || !vnoteCanvas) throw new Error('no_dom');
            vnoteVideo.srcObject = stream;
            vnoteVideo.muted = true;
            vnoteVideo.playsInline = true;
            return vnoteVideo.play().then(function () {
                vnoteCanvas.width = VNOTE_SIZE;
                vnoteCanvas.height = VNOTE_SIZE;
                vnoteLoop();
            });
        }).catch(function () {
            state.showToast('Нет доступа к камере');
        });
    }

    function stopVnote() {
        if (!vnoteActive || !vnoteRecorder) return;
        if (vnoteRecorder._timer) {
            clearInterval(vnoteRecorder._timer);
            vnoteRecorder._timer = null;
        }
        try {
            if (vnoteRecorder.state === 'recording') vnoteRecorder.stop();
        } catch (e) {
            cancelVnote();
        }
    }

    function startVnote() {
        if (vnoteActive || voiceActive) return;
        if (!vnoteStream) {
            state.showToast('Сначала откройте запись кружка');
            return;
        }
        vnoteChunks = [];
        var mime = pickMime([
            'video/webm;codecs=vp9,opus',
            'video/webm;codecs=vp8,opus',
            'video/webm',
            'video/mp4',
        ]);
        try {
            vnoteRecorder = mime
                ? new MediaRecorder(vnoteStream, { mimeType: mime })
                : new MediaRecorder(vnoteStream);
        } catch (e) {
            vnoteRecorder = new MediaRecorder(vnoteStream);
        }
        mime = vnoteRecorder.mimeType || mime;
        vnoteRecorder.ondataavailable = function (e) {
            if (e.data && e.data.size) vnoteChunks.push(e.data);
        };
        vnoteRecorder.onstop = function () {
            var dur = Math.round((Date.now() - vnoteStartedAt) / 1000);
            vnoteActive = false;
            setVnoteUi(false);
            if (vnoteRaf) {
                cancelAnimationFrame(vnoteRaf);
                vnoteRaf = null;
            }
            stopStream(vnoteStream);
            vnoteStream = null;
            var blob = new Blob(vnoteChunks, { type: mime || 'video/webm' });
            vnoteChunks = [];
            closeVnoteOverlay();
            if (!blob.size || dur < 1) {
                state.showToast('Запись слишком короткая');
                return;
            }
            var name = 'vnote_' + Date.now() + extForMime(mime);
            uploadBlob(blob, name, 'video_note', dur)
                .catch(function (err) {
                    var msg = err && err.error ? err.error : 'Не удалось отправить кружок';
                    state.showToast(msg);
                });
        };
        vnoteRecorder.onerror = function () {
            cancelVnote();
            state.showToast('Ошибка записи видео');
        };
        vnoteStartedAt = Date.now();
        vnoteActive = true;
        vnoteRecorder.start(250);
        setVnoteUi(true, 0);
        vnoteRecorder._timer = setInterval(function () {
            var sec = (Date.now() - vnoteStartedAt) / 1000;
            setVnoteUi(true, sec);
            if (sec >= VNOTE_MAX_SEC) stopVnote();
        }, 200);
    }

    function openVideoNote() {
        if (voiceActive) return;
        openVnoteOverlay();
        prepareVnotePreview();
    }

    function bindUi() {
        var voiceBtn = document.getElementById('chat-voice-btn');
        var vnoteBtn = document.getElementById('chat-vnote-btn');
        var voiceCancel = document.getElementById('voice-record-cancel');
        var vnoteClose = document.getElementById('vnote-close-btn');
        var vnoteRec = document.getElementById('vnote-record-btn');

        if (voiceBtn) {
            voiceBtn.addEventListener('click', function (e) {
                e.preventDefault();
                toggleVoice();
            });
        }
        if (voiceCancel) {
            voiceCancel.addEventListener('click', function (e) {
                e.preventDefault();
                cancelVoice();
            });
        }
        if (vnoteBtn) {
            vnoteBtn.addEventListener('click', function (e) {
                e.preventDefault();
                openVideoNote();
            });
        }
        if (vnoteClose) {
            vnoteClose.addEventListener('click', function (e) {
                e.preventDefault();
                closeVnoteOverlay();
            });
        }
        if (vnoteRec) {
            vnoteRec.addEventListener('click', function (e) {
                e.preventDefault();
                if (vnoteActive) stopVnote();
                else startVnote();
            });
        }
        var vnoteOverlay = document.getElementById('vnote-overlay');
        if (vnoteOverlay) {
            vnoteOverlay.addEventListener('click', function (e) {
                if (e.target === vnoteOverlay && !vnoteActive) closeVnoteOverlay();
            });
        }
    }

    global.WBChatMedia = {
        init: function (opts) {
            state.conversationId = opts.conversationId;
            state.csrfToken = opts.csrfToken || '';
            state.uploadFn = opts.uploadFn;
            state.showToast = opts.showToast || function () {};
            state.onLockInput = opts.onLockInput || function () {};
            state.getReplyToId = opts.getReplyToId || function () { return null; };
            bindUi();
        },
        cancelAll: function () {
            cancelVoice();
            closeVnoteOverlay();
        },
        isRecording: function () {
            return voiceActive || vnoteActive;
        },
    };
})(window);
