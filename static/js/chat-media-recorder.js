/**
 * Голосовые и видео-кружки для чата WB Hub.
 * Голос: микрофон → «Отправить». Кружок: оверлей → «Отправить» / «Закрыть».
 */
(function (global) {
    'use strict';

    var VOICE_MAX_SEC = 300;
    var VNOTE_MAX_SEC = 60;
    var VNOTE_SIZE = 384;
    var VNOTE_FPS = 20;
    var VNOTE_VIDEO_BPS = 650000;
    var VNOTE_AUDIO_BPS = 48000;
    var VNOTE_RING_LEN = 289.03;
    var RECORDER_SLICE_MS = 250;

    var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
        (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

    var state = {
        uploadFn: null,
        showToast: function () {},
        onLockInput: function () {},
        getReplyToId: function () { return null; },
        onVoicePendingChange: function () {},
        onActivityChange: function () {},
    };

    var voiceRec = null;
    var voiceChunks = [];
    var voiceStream = null;
    var voiceActive = false;
    var voiceStartedAt = 0;
    var voiceTimer = null;
    var voicePending = null;
    var voiceUploading = false;

    var vnoteStream = null;
    var vnoteRecorder = null;
    var vnoteChunks = [];
    var vnoteRaf = null;
    var vnoteActive = false;
    var vnoteStartedAt = 0;
    var vnoteTimer = null;
    var vnotePending = null;
    var vnoteDiscardOnStop = false;
    var vnoteUploading = false;
    var vnoteVideo = null;
    var vnoteCanvas = null;

    function pickMime(candidates) {
        if (!global.MediaRecorder || !MediaRecorder.isTypeSupported) return '';
        for (var i = 0; i < candidates.length; i++) {
            if (MediaRecorder.isTypeSupported(candidates[i])) return candidates[i];
        }
        return '';
    }

    function voiceMimeCandidates() {
        if (isIOS) return ['audio/mp4', 'audio/aac', 'audio/webm'];
        return ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    }

    function vnoteMimeCandidates() {
        if (isIOS) return ['video/mp4', 'video/webm'];
        return ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4'];
    }

    function extForMime(mime, variant) {
        if (!mime) return variant === 'voice' ? (isIOS ? '.m4a' : '.webm') : (isIOS ? '.mp4' : '.webm');
        if (mime.indexOf('mp4') !== -1) return variant === 'voice' ? '.m4a' : '.mp4';
        if (mime.indexOf('aac') !== -1) return '.m4a';
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
        stream.getTracks().forEach(function (t) {
            try { t.stop(); } catch (e) { /* ignore */ }
        });
    }

    function setActivity(kind, active) {
        if (state.onActivityChange) state.onActivityChange(kind, !!active);
    }

    function notifyVoicePending() {
        if (state.onVoicePendingChange) {
            state.onVoicePendingChange(!!voicePending, voiceActive);
        }
        updateSendButtonState();
    }

    function updateSendButtonState() {
        var sendBtn = document.getElementById('send-btn');
        if (!sendBtn) return;
        var ready = voiceActive || voicePending;
        sendBtn.classList.toggle('has-voice-pending', !!ready);
        sendBtn.title = voiceActive
            ? 'Остановить запись и отправить'
            : (voicePending ? 'Отправить голосовое' : 'Отправить');
    }

    function setVoiceUi(mode, sec) {
        var btn = document.getElementById('chat-voice-btn');
        var panel = document.getElementById('voice-record-panel');
        var timer = document.getElementById('voice-record-timer');
        var hint = document.querySelector('.voice-record-hint');
        if (btn) {
            btn.classList.toggle('is-recording', mode === 'recording');
            btn.classList.toggle('has-pending', mode === 'ready');
        }
        if (panel) panel.classList.toggle('active', mode === 'recording' || mode === 'ready');
        if (timer && sec != null) timer.textContent = formatDuration(sec);
        if (hint) {
            if (mode === 'recording') {
                hint.textContent = 'Идёт запись — нажмите «Отправить»';
            } else if (mode === 'ready') {
                hint.textContent = 'Готово — нажмите «Отправить»';
            } else {
                hint.textContent = 'Нажмите микрофон для записи';
            }
        }
    }

    function uploadBlob(blob, filename, variant, durationSec) {
        if (!state.uploadFn) return Promise.reject(new Error('no_upload'));
        var fd = new FormData();
        fd.append('files', blob, filename);
        fd.append('variant', variant);
        if (durationSec != null) fd.append('duration', String(durationSec));
        var reply = state.getReplyToId ? state.getReplyToId() : null;
        if (reply) fd.append('reply_to', String(reply));
        state.onLockInput(true);
        return state.uploadFn(fd).finally(function () {
            state.onLockInput(false);
        });
    }

    function clearVoiceTimer() {
        if (voiceTimer) {
            clearInterval(voiceTimer);
            voiceTimer = null;
        }
    }

    function resetVoice() {
        clearVoiceTimer();
        var wasActive = voiceActive;
        voiceActive = false;
        voicePending = null;
        voiceChunks = [];
        if (voiceRec && voiceRec.state !== 'inactive') {
            try { voiceRec.stop(); } catch (e) { /* ignore */ }
        }
        voiceRec = null;
        stopStream(voiceStream);
        voiceStream = null;
        setVoiceUi('idle');
        notifyVoicePending();
        if (wasActive) setActivity('voice', false);
    }

    function cancelVoice() {
        resetVoice();
    }

    function stopVoiceRecorder(collectPending) {
        if (!voiceRec || voiceRec.state === 'inactive') {
            if (collectPending && voiceChunks.length) {
                var mime0 = 'audio/webm';
                voicePending = {
                    blob: new Blob(voiceChunks, { type: mime0 }),
                    mime: mime0,
                    duration: Math.max(1, Math.round((Date.now() - voiceStartedAt) / 1000)),
                };
                voiceChunks = [];
            }
            stopStream(voiceStream);
            voiceStream = null;
            voiceActive = false;
            clearVoiceTimer();
            setActivity('voice', false);
            if (voicePending) setVoiceUi('ready', voicePending.duration);
            else setVoiceUi('idle');
            notifyVoicePending();
            return Promise.resolve(voicePending);
        }

        return new Promise(function (resolve) {
            var mime = voiceRec.mimeType || 'audio/webm';
            var rec = voiceRec;
            rec.onstop = function () {
                clearVoiceTimer();
                stopStream(voiceStream);
                voiceStream = null;
                voiceActive = false;
                voiceRec = null;
                setActivity('voice', false);
                var dur = Math.max(1, Math.round((Date.now() - voiceStartedAt) / 1000));
                var blob = new Blob(voiceChunks, { type: mime });
                voiceChunks = [];

                if (collectPending && blob.size) {
                    voicePending = { blob: blob, mime: mime, duration: dur };
                    setVoiceUi('ready', dur);
                    resolve(voicePending);
                } else {
                    setVoiceUi('idle');
                    resolve(null);
                }
                notifyVoicePending();
            };
            try {
                if (rec.state === 'recording') rec.requestData();
                rec.stop();
            } catch (e) {
                rec.onstop();
            }
        });
    }

    function startVoice() {
        if (voiceActive || voicePending || vnoteActive || voiceUploading) return;
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            state.showToast('Микрофон недоступен');
            return;
        }
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                voiceStream = stream;
                voiceChunks = [];
                voicePending = null;
                var mime = pickMime(voiceMimeCandidates());
                try {
                    voiceRec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
                } catch (e) {
                    voiceRec = new MediaRecorder(stream);
                }
                mime = voiceRec.mimeType || mime;
                voiceRec.ondataavailable = function (e) {
                    if (e.data && e.data.size) voiceChunks.push(e.data);
                };
                voiceRec.onerror = function () {
                    state.showToast('Ошибка записи');
                    cancelVoice();
                };
                voiceStartedAt = Date.now();
                voiceActive = true;
                voiceRec.start(RECORDER_SLICE_MS);
                setVoiceUi('recording', 0);
                setActivity('voice', true);
                notifyVoicePending();
                voiceTimer = setInterval(function () {
                    var sec = (Date.now() - voiceStartedAt) / 1000;
                    setVoiceUi('recording', sec);
                    if (sec >= VOICE_MAX_SEC) commitVoice();
                }, 200);
            })
            .catch(function () {
                state.showToast('Нет доступа к микрофону');
            });
    }

    function commitVoice() {
        if (voiceUploading) return Promise.resolve(null);
        if (!voiceActive && !voicePending) return Promise.resolve(null);

        voiceUploading = true;
        var chain = voiceActive ? stopVoiceRecorder(true) : Promise.resolve(voicePending);

        return chain.then(function (pending) {
            if (!pending || !pending.blob || !pending.blob.size) {
                state.showToast('Запись пуста');
                return Promise.reject(new Error('empty'));
            }
            voicePending = null;
            setVoiceUi('idle');
            notifyVoicePending();
            return uploadBlob(
                pending.blob,
                'voice_' + Date.now() + extForMime(pending.mime, 'voice'),
                'voice',
                pending.duration
            );
        }).finally(function () {
            voiceUploading = false;
            voicePending = null;
            setVoiceUi('idle');
            notifyVoicePending();
        });
    }

    function hasPendingVoice() {
        return voiceActive || !!voicePending;
    }

    function updateVnoteRing(sec) {
        var circle = document.getElementById('vnote-ring-progress');
        if (!circle) return;
        var pct = Math.min(1, Math.max(0, (sec || 0) / VNOTE_MAX_SEC));
        circle.style.strokeDashoffset = String(VNOTE_RING_LEN * (1 - pct));
    }

    function resetVnoteRing() {
        updateVnoteRing(0);
    }

    function setVnoteUi(active, sec) {
        var overlay = document.getElementById('vnote-overlay');
        var timer = document.getElementById('vnote-timer');
        var recBtn = document.getElementById('vnote-record-btn');
        var sendBtn = document.getElementById('vnote-send-btn');
        if (overlay) overlay.classList.toggle('is-recording', !!active);
        if (recBtn) recBtn.classList.toggle('is-recording', !!active);
        if (sendBtn) sendBtn.disabled = false;
        if (timer && sec != null) timer.textContent = formatDuration(sec);
        if (sec != null) updateVnoteRing(sec);
        if (!active) resetVnoteRing();
    }

    function cleanupVnoteUi() {
        var overlay = document.getElementById('vnote-overlay');
        if (overlay) overlay.classList.remove('active', 'is-recording');
        if (vnoteRaf) {
            cancelAnimationFrame(vnoteRaf);
            vnoteRaf = null;
        }
        setVnoteUi(false, 0);
        vnoteVideo = null;
        vnoteCanvas = null;
    }

    function clearVnoteTimer() {
        if (vnoteTimer) {
            clearInterval(vnoteTimer);
            vnoteTimer = null;
        }
    }

    function shutdownVnote() {
        clearVnoteTimer();
        var wasActive = vnoteActive;
        vnoteActive = false;
        vnotePending = null;
        vnoteChunks = [];
        vnoteDiscardOnStop = false;
        if (vnoteRecorder && vnoteRecorder.state !== 'inactive') {
            try { vnoteRecorder.stop(); } catch (e) { /* ignore */ }
        }
        vnoteRecorder = null;
        stopStream(vnoteStream);
        vnoteStream = null;
        cleanupVnoteUi();
        if (wasActive) setActivity('video_note', false);
    }

    function closeVnoteOverlay() {
        vnoteDiscardOnStop = true;
        setActivity('video_note', false);
        if (vnoteActive && vnoteRecorder) {
            try {
                if (vnoteRecorder.state === 'recording') vnoteRecorder.requestData();
                vnoteRecorder.stop();
            } catch (e) {
                shutdownVnote();
            }
            setTimeout(shutdownVnote, 300);
        } else {
            shutdownVnote();
        }
    }

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

    function getVnoteRecordStream() {
        if (!vnoteCanvas || !vnoteStream) return vnoteStream;
        try {
            if (typeof vnoteCanvas.captureStream !== 'function') return vnoteStream;
            var canvasStream = vnoteCanvas.captureStream(VNOTE_FPS);
            var videoTrack = canvasStream.getVideoTracks()[0];
            if (!videoTrack) return vnoteStream;
            var tracks = [videoTrack];
            var audioTracks = vnoteStream.getAudioTracks();
            if (audioTracks.length) tracks.push(audioTracks[0]);
            return new MediaStream(tracks);
        } catch (e) {
            return vnoteStream;
        }
    }

    function createVnoteRecorder(stream, mime) {
        var opts = {};
        if (mime) opts.mimeType = mime;
        if (mime && mime.indexOf('video') === 0) {
            opts.videoBitsPerSecond = VNOTE_VIDEO_BPS;
            opts.audioBitsPerSecond = VNOTE_AUDIO_BPS;
        }
        try {
            return Object.keys(opts).length
                ? new MediaRecorder(stream, opts)
                : new MediaRecorder(stream);
        } catch (e) {
            try {
                return mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
            } catch (e2) {
                return new MediaRecorder(stream);
            }
        }
    }

    function prepareVnotePreview() {
        return navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'user',
                width: { ideal: 480, max: 640 },
                height: { ideal: 480, max: 640 },
            },
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
            },
        }).then(function (stream) {
            vnoteStream = stream;
            vnoteVideo = document.getElementById('vnote-preview-video');
            vnoteCanvas = document.getElementById('vnote-preview-canvas');
            if (!vnoteVideo || !vnoteCanvas) throw new Error('no_dom');
            vnoteVideo.srcObject = stream;
            vnoteVideo.muted = true;
            vnoteVideo.setAttribute('playsinline', 'true');
            vnoteVideo.setAttribute('webkit-playsinline', 'true');
            return vnoteVideo.play();
        }).then(function () {
            vnoteCanvas.width = VNOTE_SIZE;
            vnoteCanvas.height = VNOTE_SIZE;
            vnoteLoop();
        });
    }

    function stopVnoteRecorder(collectPending) {
        if (!vnoteRecorder || vnoteRecorder.state === 'inactive') {
            return Promise.resolve(vnotePending);
        }
        return new Promise(function (resolve) {
            var mime = vnoteRecorder.mimeType || 'video/webm';
            var rec = vnoteRecorder;
            rec.onstop = function () {
                setTimeout(function () {
                    clearVnoteTimer();
                    vnoteActive = false;
                    setActivity('video_note', false);
                    var dur = Math.max(1, Math.round((Date.now() - vnoteStartedAt) / 1000));
                    var blob = new Blob(vnoteChunks, { type: mime });
                    vnoteChunks = [];
                    vnoteRecorder = null;

                    if (vnoteDiscardOnStop) {
                        vnoteDiscardOnStop = false;
                        stopStream(vnoteStream);
                        vnoteStream = null;
                        setVnoteUi(false, 0);
                        resolve(null);
                        return;
                    }

                    if (collectPending && blob.size) {
                        vnotePending = { blob: blob, mime: mime, duration: dur };
                        setVnoteUi(false, dur);
                        resolve(vnotePending);
                    } else {
                        vnotePending = null;
                        setVnoteUi(false, 0);
                        resolve(null);
                    }
                }, isIOS ? 120 : 0);
            };
            try {
                if (rec.state === 'recording') rec.requestData();
                rec.stop();
            } catch (e) {
                rec.onstop();
            }
        });
    }

    function startVnote() {
        if (vnoteActive || !vnoteStream || vnoteUploading) return;
        vnoteChunks = [];
        vnotePending = null;
        var recordStream = getVnoteRecordStream() || vnoteStream;
        var mime = pickMime(vnoteMimeCandidates());
        vnoteRecorder = createVnoteRecorder(recordStream, mime);
        mime = vnoteRecorder.mimeType || mime;
        vnoteRecorder.ondataavailable = function (e) {
            if (e.data && e.data.size) vnoteChunks.push(e.data);
        };
        vnoteRecorder.onerror = function () {
            state.showToast('Ошибка записи');
            vnoteActive = false;
            setActivity('video_note', false);
            setVnoteUi(false, 0);
        };
        vnoteStartedAt = Date.now();
        vnoteActive = true;
        vnoteDiscardOnStop = false;
        vnoteRecorder.start(RECORDER_SLICE_MS);
        setVnoteUi(true, 0);
        setActivity('video_note', true);
        vnoteTimer = setInterval(function () {
            var sec = (Date.now() - vnoteStartedAt) / 1000;
            setVnoteUi(true, sec);
            if (sec >= VNOTE_MAX_SEC) commitVnote();
        }, 200);
    }

    function commitVnote() {
        if (vnoteUploading) return Promise.resolve(null);
        if (!vnoteActive && !vnotePending) {
            state.showToast('Сначала запишите кружок');
            return Promise.reject(new Error('empty'));
        }

        vnoteUploading = true;
        var chain = vnoteActive ? stopVnoteRecorder(true) : Promise.resolve(vnotePending);

        return chain.then(function (pending) {
            var p = pending || vnotePending;
            if (!p || !p.blob || !p.blob.size) {
                state.showToast('Запись пуста — попробуйте ещё раз');
                return Promise.reject(new Error('empty'));
            }
            state.showToast('Отправка…');
            return uploadBlob(
                p.blob,
                'vnote_' + Date.now() + extForMime(p.mime, 'video_note'),
                'video_note',
                p.duration
            ).then(function (res) {
                vnotePending = null;
                stopStream(vnoteStream);
                vnoteStream = null;
                cleanupVnoteUi();
                return res;
            });
        }).catch(function (err) {
            if (err && err.error) state.showToast(err.error);
            else if (err && err.message !== 'empty') state.showToast('Не удалось отправить кружок');
            throw err;
        }).finally(function () {
            vnoteUploading = false;
        });
    }

    function openVideoNote() {
        if (voiceActive || voicePending || voiceUploading) {
            state.showToast('Сначала завершите голосовое');
            return;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            state.showToast('Камера недоступна');
            return;
        }
        var overlay = document.getElementById('vnote-overlay');
        if (overlay) overlay.classList.add('active');
        resetVnoteRing();
        setVnoteUi(false, 0);
        vnotePending = null;
        vnoteDiscardOnStop = false;
        prepareVnotePreview().catch(function () {
            state.showToast('Нет доступа к камере');
            cleanupVnoteUi();
        });
    }

    function bindUi() {
        var voiceBtn = document.getElementById('chat-voice-btn');
        var voiceCancel = document.getElementById('voice-record-cancel');
        var vnoteBtn = document.getElementById('chat-vnote-btn');
        var vnoteClose = document.getElementById('vnote-close-btn');
        var vnoteSend = document.getElementById('vnote-send-btn');
        var vnoteRec = document.getElementById('vnote-record-btn');
        var vnoteOverlay = document.getElementById('vnote-overlay');
        var vnotePanel = document.querySelector('.vnote-panel');

        if (voiceBtn) {
            voiceBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (voiceActive || voicePending) {
                    state.showToast('Отправьте голосовое кнопкой «Отправить» или «Отмена»');
                    return;
                }
                startVoice();
            });
        }
        if (voiceCancel) {
            voiceCancel.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                cancelVoice();
            });
        }
        if (vnoteBtn) {
            vnoteBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                openVideoNote();
            });
        }
        if (vnoteClose) {
            vnoteClose.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                closeVnoteOverlay();
            });
        }
        if (vnoteSend) {
            vnoteSend.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                commitVnote();
            });
        }
        if (vnoteRec) {
            vnoteRec.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (vnoteActive) {
                    stopVnoteRecorder(true);
                } else {
                    startVnote();
                }
            });
        }
        if (vnoteOverlay) {
            vnoteOverlay.addEventListener('click', function (e) {
                if (e.target === vnoteOverlay && !vnoteActive) {
                    closeVnoteOverlay();
                }
            });
        }
        if (vnotePanel) {
            vnotePanel.addEventListener('click', function (e) {
                e.stopPropagation();
            });
        }
    }

    global.WBChatMedia = {
        init: function (opts) {
            state.uploadFn = opts.uploadFn;
            state.showToast = opts.showToast || function () {};
            state.onLockInput = opts.onLockInput || function () {};
            state.getReplyToId = opts.getReplyToId || function () { return null; };
            state.onVoicePendingChange = opts.onVoicePendingChange || function () {};
            state.onActivityChange = opts.onActivityChange || function () {};
            bindUi();
            notifyVoicePending();
        },
        cancelAll: function () {
            cancelVoice();
            closeVnoteOverlay();
        },
        /** Только активная запись кружка (не голос). */
        isRecording: function () {
            return vnoteActive;
        },
        isVoiceRecording: function () {
            return voiceActive;
        },
        isVnoteRecording: function () {
            return vnoteActive;
        },
        hasPendingVoice: hasPendingVoice,
        commitVoice: commitVoice,
        commitVnote: commitVnote,
    };
})(window);
