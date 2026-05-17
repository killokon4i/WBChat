"""
Сервис для работы с профилем сотрудника.
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from org.models import EmployeeChangeLog

User = get_user_model()


class ProfileService:
    """
    Сервис управления профилем:
    - Обновление личных данных
    - Логирование изменений
    - Работа с проектами
    """

    EDITABLE_FIELDS = [
        'avatar', 'personal_phone', 'personal_email',
        'telegram', 'whatsapp', 'about',
        'show_birth_date', 'show_personal_phone', 'show_personal_email'
    ]

    def update_profile(self, user, data: dict, changed_by=None) -> User:
        """
        Обновить профиль пользователя.
        
        Args:
            user: Пользователь
            data: Словарь с данными для обновления
            changed_by: Кто вносит изменения (если не сам пользователь)
        
        Returns:
            Обновлённый пользователь
        """
        changed_by = changed_by or user
        changes = []
        
        for field in self.EDITABLE_FIELDS:
            if field in data and data[field] != getattr(user, field):
                old_value = str(getattr(user, field) or '')
                new_value = str(data[field] or '')
                
                setattr(user, field, data[field])
                
                changes.append({
                    'field': field,
                    'old_value': old_value,
                    'new_value': new_value,
                })
        
        if changes:
            user.save(update_fields=self.EDITABLE_FIELDS)
            
            # Логируем изменения
            for change in changes:
                EmployeeChangeLog.objects.create(
                    employee=user,
                    field_name=change['field'],
                    old_value=change['old_value'],
                    new_value=change['new_value'],
                    changed_by=changed_by,
                    source='manual'
                )
        
        return user

    def set_status(
        self,
        user,
        status: str,
        end_date=None,
        substitute=None,
        changed_by=None
    ) -> User:
        """
        Установить статус сотрудника.
        
        Args:
            user: Пользователь
            status: Новый статус
            end_date: Дата окончания статуса
            substitute: Замещающий сотрудник
            changed_by: Кто меняет статус
        """
        from org.models import EmployeeStatusLog
        
        old_status = user.status
        
        user.status = status
        user.status_end_date = end_date
        user.substitute = substitute
        user.save(update_fields=['status', 'status_end_date', 'substitute'])
        
        # Логируем изменение статуса
        EmployeeStatusLog.objects.create(
            employee=user,
            status=status,
            start_date=timezone.now().date(),
            end_date=end_date,
            substitute=substitute,
            created_by=changed_by or user,
        )
        
        # Логируем изменение поля
        EmployeeChangeLog.objects.create(
            employee=user,
            field_name='status',
            old_value=old_status,
            new_value=status,
            changed_by=changed_by or user,
            source='manual'
        )
        
        return user

    def add_project(
        self,
        user,
        name: str,
        role: str = '',
        description: str = '',
        start_date=None,
        end_date=None
    ):
        """
        Добавить проект к профилю сотрудника.
        """
        from accounts.models import EmployeeProject
        
        return EmployeeProject.objects.create(
            employee=user,
            name=name,
            role=role,
            description=description,
            start_date=start_date,
            end_date=end_date,
            is_current=end_date is None,
            source='manual'
        )

    def get_profile_completeness(self, user) -> dict:
        """
        Рассчитать полноту заполнения профиля.
        
        Returns:
            Словарь с процентом заполненности и пустыми полями
        """
        fields_to_check = [
            ('avatar', 'Фото профиля'),
            ('personal_phone', 'Личный телефон'),
            ('telegram', 'Telegram'),
            ('about', 'О себе'),
        ]
        
        filled = 0
        empty_fields = []
        
        for field, label in fields_to_check:
            value = getattr(user, field)
            if value:
                filled += 1
            else:
                empty_fields.append(label)
        
        percentage = int(filled / len(fields_to_check) * 100)
        
        return {
            'percentage': percentage,
            'filled': filled,
            'total': len(fields_to_check),
            'empty_fields': empty_fields,
        }


