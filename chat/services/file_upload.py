"""Проверка вложений чата перед загрузкой."""
import os

CHAT_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 МБ
CHAT_VOICE_MAX_BYTES = 10 * 1024 * 1024  # 10 МБ
CHAT_VIDEO_NOTE_MAX_BYTES = 20 * 1024 * 1024  # 20 МБ
CHAT_VOICE_MAX_DURATION_SEC = 300  # 5 мин
CHAT_VIDEO_NOTE_MAX_DURATION_SEC = 60  # как в Telegram

CHAT_VOICE_EXTENSIONS = frozenset({'.webm', '.ogg', '.opus', '.m4a', '.mp4', '.mp3', '.wav'})
CHAT_VIDEO_NOTE_EXTENSIONS = frozenset({'.webm', '.mp4', '.mov', '.m4v'})

# Исполняемые и опасные расширения (в т.ч. .exe)
CHAT_BLOCKED_EXTENSIONS = frozenset({
    '.exe',
    '.bat',
    '.cmd',
    '.com',
    '.msi',
    '.scr',
    '.pif',
    '.vbs',
    '.js',
    '.wsf',
    '.ps1',
    '.sh',
    '.jar',
    '.dll',
    '.apk',
    '.deb',
    '.rpm',
})

CHAT_BLOCKED_MIME_PREFIXES = (
    'application/x-msdownload',
    'application/vnd.microsoft.portable-executable',
    'application/x-executable',
    'application/x-dosexec',
)


def file_extension(name: str) -> str:
    """Расширение файла в нижнем регистре, включая .tar.gz → .gz."""
    base = os.path.basename(name or '')
    lower = base.lower()
    for ext in ('.tar.gz', '.tar.bz2', '.tar.xz'):
        if lower.endswith(ext):
            return ext
    return os.path.splitext(lower)[1]


def validate_chat_upload_file(filename: str, size: int, mime_type=None):
    """
    Проверить файл. Вернуть текст ошибки или None, если можно загружать.
    """
    name = (filename or 'file').strip()
    if not name:
        return 'Имя файла не указано'

    try:
        size = int(size)
    except (TypeError, ValueError):
        return 'Некорректный размер файла'

    if size <= 0:
        return f'Файл пустой: {name}'

    if size > CHAT_MAX_FILE_BYTES:
        return f'Файл «{name}» слишком большой (максимум 50 МБ)'

    ext = file_extension(name)
    if ext in CHAT_BLOCKED_EXTENSIONS:
        if ext == '.exe':
            return f'Файлы .exe запрещены: {name}'
        return f'Запрещённый тип файла ({ext}): {name}'

    mime = (mime_type or '').lower().split(';', 1)[0].strip()
    if mime:
        for blocked in CHAT_BLOCKED_MIME_PREFIXES:
            if mime.startswith(blocked):
                return f'Запрещённый тип файла: {name}'

    return None


def validate_chat_upload_variant(filename: str, size: int, mime_type=None, variant='default', duration_sec=None):
    """
    Доп. проверки для голосовых и кружков. variant: default | voice | video_note.
    """
    if variant not in ('voice', 'video_note'):
        return validate_chat_upload_file(filename, size, mime_type)

    name = (filename or 'file').strip()
    ext = file_extension(name)
    mime = (mime_type or '').lower().split(';', 1)[0].strip()

    if variant == 'voice':
        max_bytes = CHAT_VOICE_MAX_BYTES
        max_dur = CHAT_VOICE_MAX_DURATION_SEC
        label = 'Голосовое сообщение'
        allowed_ext = CHAT_VOICE_EXTENSIONS
        mime_ok = (
            mime.startswith('audio/')
            or mime in ('video/webm', 'application/ogg', 'application/octet-stream')
        )
    else:
        max_bytes = CHAT_VIDEO_NOTE_MAX_BYTES
        max_dur = CHAT_VIDEO_NOTE_MAX_DURATION_SEC
        label = 'Видеосообщение'
        allowed_ext = CHAT_VIDEO_NOTE_EXTENSIONS
        mime_ok = mime.startswith('video/') or mime in ('video/quicktime', 'application/octet-stream')

    if size > max_bytes:
        mb = max_bytes // (1024 * 1024)
        return f'{label}: файл слишком большой (максимум {mb} МБ)'

    if ext and ext not in allowed_ext:
        return f'{label}: неподдерживаемый формат ({ext})'

    if mime and not mime_ok:
        return f'{label}: неподдерживаемый тип ({mime})'

    if duration_sec is not None:
        try:
            duration_sec = int(duration_sec)
        except (TypeError, ValueError):
            duration_sec = None
        if duration_sec is not None and duration_sec > max_dur:
            return f'{label}: слишком длинная запись (максимум {max_dur} с)'

    return validate_chat_upload_file(filename, size, mime_type)
