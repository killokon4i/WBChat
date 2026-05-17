from django.db import models
from django.conf import settings


class Department(models.Model):
    """
    Подразделение (иерархическая структура).
    Использует Materialized Path для эффективных иерархических запросов.
    """
    name = models.CharField('Название', max_length=255)
    code = models.CharField('Код', max_length=50, unique=True)
    description = models.TextField('Описание', blank=True)
    
    # Иерархия
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительское подразделение'
    )
    level = models.PositiveIntegerField('Уровень вложенности', default=0)
    path = models.CharField('Materialized Path', max_length=500, blank=True, db_index=True)
    
    # Руководство
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments',
        verbose_name='Руководитель'
    )
    
    # Статус
    is_active = models.BooleanField('Активно', default=True)
    
    # Внешние системы
    external_id = models.CharField('ID в 1С', max_length=100, null=True, blank=True, unique=True)
    
    # Служебные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'
        ordering = ['path', 'name']
        indexes = [
            models.Index(fields=['path']),
            models.Index(fields=['parent', 'is_active']),
            models.Index(fields=['external_id']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Обновляем уровень и путь
        if self.parent:
            self.level = self.parent.level + 1
            self.path = f"{self.parent.path}/{self.code}" if self.parent.path else self.code
        else:
            self.level = 0
            self.path = self.code
        super().save(*args, **kwargs)

    def get_ancestors(self):
        """Получить всех предков"""
        if not self.parent:
            return Department.objects.none()
        
        ancestor_codes = self.path.split('/')[:-1]
        return Department.objects.filter(code__in=ancestor_codes).order_by('level')

    def get_descendants(self):
        """Получить всех потомков"""
        return Department.objects.filter(path__startswith=f"{self.path}/")

    def get_employees(self):
        """Получить всех сотрудников подразделения"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(department=self, is_archived=False)


class Position(models.Model):
    """Должность"""
    name = models.CharField('Название', max_length=255)
    code = models.CharField('Код', max_length=50, unique=True)
    description = models.TextField('Описание', blank=True)
    
    # Связь с подразделением (опционально)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='positions',
        verbose_name='Подразделение'
    )
    
    # Характеристики
    is_manager = models.BooleanField('Руководящая должность', default=False)
    grade_min = models.CharField('Минимальный грейд', max_length=10, blank=True)
    grade_max = models.CharField('Максимальный грейд', max_length=10, blank=True)
    
    # Внешние системы
    external_id = models.CharField('ID в 1С', max_length=100, null=True, blank=True, unique=True)
    
    # Служебные
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'
        ordering = ['name']

    def __str__(self):
        return self.name


class EmployeeStatusLog(models.Model):
    """
    Журнал изменений статусов сотрудников.
    Отслеживает отпуска, больничные, командировки и т.д.
    """
    STATUS_CHOICES = [
        ('active', 'Работает'),
        ('vacation', 'В отпуске'),
        ('sick_leave', 'На больничном'),
        ('business_trip', 'В командировке'),
        ('maternity', 'В декрете'),
        ('unpaid_leave', 'Отпуск без содержания'),
        ('terminated', 'Уволен'),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='status_logs',
        verbose_name='Сотрудник'
    )
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES)
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания', null=True, blank=True)
    
    # Замещение
    substitute = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='substituting_in_logs',
        verbose_name='Замещающий'
    )
    
    # Примечание
    note = models.TextField('Примечание', blank=True)
    
    # Создание
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_status_logs',
        verbose_name='Создал'
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Запись статуса сотрудника'
        verbose_name_plural = 'Журнал статусов сотрудников'
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['employee', '-start_date']),
            models.Index(fields=['status', 'start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.employee} - {self.get_status_display()} ({self.start_date})"


class EmployeeChangeLog(models.Model):
    """
    Журнал всех изменений данных сотрудника.
    Для аудита и отслеживания истории.
    """
    SOURCE_CHOICES = [
        ('manual', 'Вручную'),
        ('hr_sync', 'Синхронизация HR'),
        ('system', 'Системное'),
        ('api', 'Через API'),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='change_logs',
        verbose_name='Сотрудник'
    )
    field_name = models.CharField('Поле', max_length=100)
    old_value = models.TextField('Старое значение', null=True, blank=True)
    new_value = models.TextField('Новое значение', null=True, blank=True)
    
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='made_changes',
        verbose_name='Изменил'
    )
    changed_at = models.DateTimeField('Дата изменения', auto_now_add=True)
    source = models.CharField('Источник', max_length=20, choices=SOURCE_CHOICES, default='manual')

    class Meta:
        verbose_name = 'Запись изменения сотрудника'
        verbose_name_plural = 'Журнал изменений сотрудников'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['employee', '-changed_at']),
            models.Index(fields=['field_name', '-changed_at']),
        ]

    def __str__(self):
        return f"{self.employee} - {self.field_name} ({self.changed_at.strftime('%d.%m.%Y %H:%M')})"

