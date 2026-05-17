"""
Сервис безопасной обработки файлов.
Валидация, антивирусная проверка, генерация превью.
"""
import os
import hashlib
import mimetypes
from typing import Tuple, Optional
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


class FileSecurityService:
    """
    Сервис безопасности файлов:
    - Валидация расширений и MIME-типов
    - Проверка размера
    - Вычисление хэшей
    - Генерация превью (заглушка)
    """

    # Разрешённые расширения по умолчанию
    ALLOWED_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.ppt', '.pptx', '.txt', '.rtf', '.odt', '.ods'
    }

    # Соответствие MIME-типов расширениям
    EXTENSION_MIME_MAP = {
        '.pdf': ['application/pdf'],
        '.doc': ['application/msword'],
        '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        '.xls': ['application/vnd.ms-excel'],
        '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        '.ppt': ['application/vnd.ms-powerpoint'],
        '.pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
        '.txt': ['text/plain'],
        '.rtf': ['application/rtf', 'text/rtf'],
        '.odt': ['application/vnd.oasis.opendocument.text'],
        '.ods': ['application/vnd.oasis.opendocument.spreadsheet'],
    }

    # Максимальный размер по умолчанию (50 MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    def __init__(self):
        # Получаем настройки из settings.py если есть
        doc_settings = getattr(settings, 'DOCUMENTS', {})
        self.max_file_size = doc_settings.get('MAX_FILE_SIZE', self.MAX_FILE_SIZE)
        self.allowed_extensions = set(
            doc_settings.get('ALLOWED_EXTENSIONS', self.ALLOWED_EXTENSIONS)
        )

    def validate_file(self, file: UploadedFile) -> Tuple[bool, str]:
        """
        Валидация файла: расширение, MIME-тип, размер.
        
        Args:
            file: Загруженный файл
            
        Returns:
            Кортеж (успех, сообщение об ошибке)
        """
        # Проверка размера
        if file.size > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            return False, f'Размер файла превышает {max_mb:.0f} МБ'

        # Проверка расширения
        _, ext = os.path.splitext(file.name.lower())
        if ext not in self.allowed_extensions:
            return False, f'Недопустимое расширение файла: {ext}'

        # Проверка MIME-типа
        mime_type = file.content_type or mimetypes.guess_type(file.name)[0]
        expected_mimes = self.EXTENSION_MIME_MAP.get(ext, [])
        
        if expected_mimes and mime_type not in expected_mimes:
            return False, f'MIME-тип ({mime_type}) не соответствует расширению ({ext})'

        # Дополнительная проверка по magic bytes (опционально)
        if not self._check_magic_bytes(file, ext):
            return False, 'Содержимое файла не соответствует его расширению'

        return True, ''

    def _check_magic_bytes(self, file: UploadedFile, ext: str) -> bool:
        """
        Проверка magic bytes файла.
        """
        magic_bytes = {
            '.pdf': b'%PDF',
            '.doc': b'\xD0\xCF\x11\xE0',  # OLE
            '.docx': b'PK\x03\x04',  # ZIP
            '.xls': b'\xD0\xCF\x11\xE0',
            '.xlsx': b'PK\x03\x04',
            '.ppt': b'\xD0\xCF\x11\xE0',
            '.pptx': b'PK\x03\x04',
        }

        expected = magic_bytes.get(ext)
        if not expected:
            return True  # Пропускаем проверку для неизвестных типов

        # Читаем первые байты
        file.seek(0)
        header = file.read(len(expected))
        file.seek(0)  # Возвращаем указатель

        return header.startswith(expected)

    def scan_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Антивирусная проверка файла.
        
        Заглушка для интеграции с антивирусом (ClamAV, Kaspersky и т.д.)
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Кортеж (чисто, результат проверки)
        """
        # TODO: Интеграция с антивирусом
        # Пример для ClamAV:
        # import clamd
        # cd = clamd.ClamdUnixSocket()
        # result = cd.scan(file_path)
        
        # Пока возвращаем "чисто"
        return True, 'clean'

    def calculate_hash(self, file: UploadedFile) -> str:
        """
        Вычисление SHA-256 хэша файла.
        
        Args:
            file: Файл
            
        Returns:
            Хэш в hex формате
        """
        sha256 = hashlib.sha256()
        
        file.seek(0)
        for chunk in file.chunks():
            sha256.update(chunk)
        file.seek(0)
        
        return sha256.hexdigest()

    def generate_preview(self, file_path: str, output_path: str) -> Tuple[bool, str]:
        """
        Генерация превью документа.
        
        Заглушка для интеграции с LibreOffice/unoconv для конвертации в PDF.
        
        Args:
            file_path: Путь к исходному файлу
            output_path: Путь для сохранения превью
            
        Returns:
            Кортеж (успех, путь к превью или ошибка)
        """
        # TODO: Интеграция с LibreOffice
        # import subprocess
        # subprocess.run([
        #     'libreoffice', '--headless', '--convert-to', 'pdf',
        #     '--outdir', os.path.dirname(output_path), file_path
        # ])
        
        # Пока возвращаем False (превью не создано)
        return False, 'Preview generation not implemented'

    def get_mime_type(self, file: UploadedFile) -> str:
        """
        Определение MIME-типа файла.
        """
        mime_type = file.content_type
        if not mime_type:
            mime_type = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
        return mime_type


