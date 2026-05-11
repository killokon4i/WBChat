"""
Сервис управления версиями документов.
"""
from typing import Optional, List
from django.utils import timezone
from django.db import transaction

from ..models import Document, DocumentVersion


class VersioningService:
    """
    Сервис версионирования документов:
    - Создание новых версий
    - Получение истории версий
    - Сравнение версий
    - Откат к предыдущей версии
    """

    def __init__(self, file_security_service=None):
        from .file_security import FileSecurityService
        self.security = file_security_service or FileSecurityService()

    @transaction.atomic
    def create_version(
        self,
        document: Document,
        file,
        user,
        comment: str = ''
    ) -> DocumentVersion:
        """
        Создать новую версию документа.
        
        Args:
            document: Документ
            file: Загруженный файл
            user: Пользователь, загружающий файл
            comment: Комментарий к версии
            
        Returns:
            Созданная версия
        """
        # Валидация файла
        is_valid, error = self.security.validate_file(file)
        if not is_valid:
            raise ValueError(error)

        # Получаем следующий номер версии
        last_version = document.versions.order_by('-version_number').first()
        next_version = (last_version.version_number + 1) if last_version else 1

        # Вычисляем хэш
        file_hash = self.security.calculate_hash(file)

        # Проверяем на дубликат
        if last_version and last_version.file_hash == file_hash:
            raise ValueError('Файл идентичен предыдущей версии')

        # Создаём версию
        version = DocumentVersion.objects.create(
            document=document,
            version_number=next_version,
            file=file,
            file_name=file.name,
            file_size=file.size,
            file_hash=file_hash,
            mime_type=self.security.get_mime_type(file),
            uploaded_by=user,
            comment=comment,
        )

        # Обновляем дату изменения документа
        document.updated_at = timezone.now()
        document.save(update_fields=['updated_at'])

        return version

    def get_version_history(self, document: Document) -> List[DocumentVersion]:
        """
        Получить историю версий документа.
        """
        return list(document.versions.select_related('uploaded_by').order_by('-version_number'))

    def get_version(self, document: Document, version_number: int) -> Optional[DocumentVersion]:
        """
        Получить конкретную версию документа.
        """
        return document.versions.filter(version_number=version_number).first()

    def compare_versions(
        self,
        document: Document,
        version1_num: int,
        version2_num: int
    ) -> dict:
        """
        Сравнить две версии документа.
        Возвращает метаданные для сравнения.
        """
        v1 = self.get_version(document, version1_num)
        v2 = self.get_version(document, version2_num)

        if not v1 or not v2:
            raise ValueError('Одна или обе версии не найдены')

        return {
            'version1': {
                'number': v1.version_number,
                'file_name': v1.file_name,
                'file_size': v1.file_size,
                'uploaded_at': v1.uploaded_at,
                'uploaded_by': v1.uploaded_by.get_full_name() if v1.uploaded_by else None,
                'comment': v1.comment,
            },
            'version2': {
                'number': v2.version_number,
                'file_name': v2.file_name,
                'file_size': v2.file_size,
                'uploaded_at': v2.uploaded_at,
                'uploaded_by': v2.uploaded_by.get_full_name() if v2.uploaded_by else None,
                'comment': v2.comment,
            },
            'size_diff': v2.file_size - v1.file_size,
            'same_content': v1.file_hash == v2.file_hash,
        }

    @transaction.atomic
    def rollback_to_version(
        self,
        document: Document,
        version_number: int,
        user,
        comment: str = ''
    ) -> DocumentVersion:
        """
        Откатить документ к указанной версии.
        Создаёт новую версию с содержимым старой.
        
        Args:
            document: Документ
            version_number: Номер версии для отката
            user: Пользователь
            comment: Комментарий
            
        Returns:
            Новая версия документа
        """
        target_version = self.get_version(document, version_number)
        if not target_version:
            raise ValueError(f'Версия {version_number} не найдена')

        # Получаем следующий номер версии
        last_version = document.versions.order_by('-version_number').first()
        next_version = last_version.version_number + 1

        # Создаём новую версию с файлом из старой
        new_version = DocumentVersion.objects.create(
            document=document,
            version_number=next_version,
            file=target_version.file,
            file_name=target_version.file_name,
            file_size=target_version.file_size,
            file_hash=target_version.file_hash,
            mime_type=target_version.mime_type,
            uploaded_by=user,
            comment=comment or f'Откат к версии {version_number}',
        )

        return new_version


