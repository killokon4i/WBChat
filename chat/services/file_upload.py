"""Проверка вложений чата перед загрузкой."""
import os

CHAT_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 МБ

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
