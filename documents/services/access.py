"""
Сервис управления доступом к документам.
"""
from typing import Dict, List, Optional
from django.db.models import Q

from ..models import Document, DocumentAccessRule, DocumentCategory


class DocumentAccessService:
    """
    Сервис проверки и управления правами доступа к документам:
    - Проверка прав пользователя
    - Назначение прав доступа
    - Получение списка доступов
    """

    PERMISSION_HIERARCHY = {
        'view': 1,
        'download': 2,
        'edit': 3,
        'delete': 4,
        'publish': 5,
        'manage_access': 6,
    }

    def check_permission(
        self,
        document: Document,
        user,
        permission: str
    ) -> bool:
        """
        Проверить право доступа пользователя к документу.
        
        Args:
            document: Документ
            user: Пользователь
            permission: Тип права (view, download, edit, delete, publish, manage_access)
            
        Returns:
            True если доступ разрешён
        """
        # Суперпользователь может всё
        if user.is_superuser:
            return True

        # Автор и куратор имеют полный доступ
        if document.author == user or document.curator == user:
            return True

        # Публичные документы можно просматривать
        if document.confidentiality == 'public' and permission == 'view':
            return True

        # Проверяем правила доступа
        permission_field = f'can_{permission}'
        
        # Прямой доступ пользователю
        user_rules = DocumentAccessRule.objects.filter(
            Q(document=document) | Q(category=document.category),
            user=user,
            **{permission_field: True}
        )
        if user_rules.exists():
            return True

        # Доступ по подразделению
        if user.department:
            dept_rules = DocumentAccessRule.objects.filter(
                Q(document=document) | Q(category=document.category),
                department=user.department,
                **{permission_field: True}
            )
            if dept_rules.exists():
                return True

        # Доступ по роли
        user_roles = self._get_user_roles(user)
        for role in user_roles:
            role_rules = DocumentAccessRule.objects.filter(
                Q(document=document) | Q(category=document.category),
                role=role,
                **{permission_field: True}
            )
            if role_rules.exists():
                return True

        return False

    def _get_user_roles(self, user) -> List[str]:
        """Получить роли пользователя"""
        roles = ['user']  # Базовая роль
        
        if user.isModerator:
            roles.append('moderator')
        if user.is_hr:
            roles.append('hr')
        if user.is_admin_portal:
            roles.append('admin')
        if user.is_staff:
            roles.append('staff')
        
        return roles

    def get_user_permissions(self, document: Document, user) -> Dict[str, bool]:
        """
        Получить все права пользователя для документа.
        
        Returns:
            Словарь {permission: allowed}
        """
        permissions = {}
        for perm in self.PERMISSION_HIERARCHY.keys():
            permissions[perm] = self.check_permission(document, user, perm)
        return permissions

    def grant_access(
        self,
        document: Document,
        target_user=None,
        target_department=None,
        target_role: str = None,
        permissions: Dict[str, bool] = None,
        granted_by=None
    ) -> DocumentAccessRule:
        """
        Предоставить доступ к документу.
        
        Args:
            document: Документ
            target_user: Целевой пользователь
            target_department: Целевое подразделение
            target_role: Целевая роль
            permissions: Словарь прав {can_view: True, ...}
            granted_by: Кто предоставляет доступ
            
        Returns:
            Созданное правило доступа
        """
        if not any([target_user, target_department, target_role]):
            raise ValueError('Необходимо указать получателя доступа')

        defaults = {
            'can_view': False,
            'can_download': False,
            'can_edit': False,
            'can_delete': False,
            'can_publish': False,
            'can_manage_access': False,
            'created_by': granted_by,
        }
        
        if permissions:
            for perm, value in permissions.items():
                field = f'can_{perm}' if not perm.startswith('can_') else perm
                if field in defaults:
                    defaults[field] = value

        rule, created = DocumentAccessRule.objects.update_or_create(
            document=document,
            user=target_user,
            department=target_department,
            role=target_role or '',
            defaults=defaults
        )

        return rule

    def revoke_access(
        self,
        document: Document,
        target_user=None,
        target_department=None,
        target_role: str = None
    ) -> bool:
        """
        Отозвать доступ к документу.
        """
        filters = {'document': document}
        
        if target_user:
            filters['user'] = target_user
        if target_department:
            filters['department'] = target_department
        if target_role:
            filters['role'] = target_role

        deleted, _ = DocumentAccessRule.objects.filter(**filters).delete()
        return deleted > 0

    def get_document_access_list(self, document: Document) -> List[Dict]:
        """
        Получить список всех правил доступа к документу.
        """
        rules = DocumentAccessRule.objects.filter(
            Q(document=document) | Q(category=document.category)
        ).select_related('user', 'department', 'created_by')

        result = []
        for rule in rules:
            result.append({
                'id': rule.id,
                'source': 'document' if rule.document else 'category',
                'target_type': 'user' if rule.user else ('department' if rule.department else 'role'),
                'target': (
                    rule.user.get_full_name() if rule.user
                    else rule.department.name if rule.department
                    else rule.role
                ),
                'permissions': {
                    'view': rule.can_view,
                    'download': rule.can_download,
                    'edit': rule.can_edit,
                    'delete': rule.can_delete,
                    'publish': rule.can_publish,
                    'manage_access': rule.can_manage_access,
                },
                'created_by': rule.created_by.get_full_name() if rule.created_by else None,
                'created_at': rule.created_at,
            })

        return result

    def copy_access_rules(
        self,
        source_document: Document,
        target_document: Document,
        copied_by=None
    ) -> int:
        """
        Скопировать правила доступа с одного документа на другой.
        """
        source_rules = DocumentAccessRule.objects.filter(document=source_document)
        count = 0

        for rule in source_rules:
            DocumentAccessRule.objects.create(
                document=target_document,
                user=rule.user,
                department=rule.department,
                role=rule.role,
                can_view=rule.can_view,
                can_download=rule.can_download,
                can_edit=rule.can_edit,
                can_delete=rule.can_delete,
                can_publish=rule.can_publish,
                can_manage_access=rule.can_manage_access,
                created_by=copied_by,
            )
            count += 1

        return count


