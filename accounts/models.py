from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """
    Расширенная модель пользователя для корпоративного портала WB Bank.
    
    Содержит:
    - HR данные (read-only, синхронизируются из 1С)
    - Редактируемые сотрудником данные
    - Статусы и замещение
    - Служебные поля
    """
    
    # === СТАТУСЫ СОТРУДНИКА ===
    STATUS_CHOICES = [
        ('active', 'Работает'),
        ('vacation', 'В отпуске'),
        ('sick_leave', 'На больничном'),
        ('business_trip', 'В командировке'),
        ('maternity', 'В декрете'),
        ('unpaid_leave', 'Отпуск без содержания'),
        ('terminated', 'Уволен'),
    ]
    
    # === HR данные (read-only, синхронизация из 1С) ===
    employee_id = models.CharField(
        'ID сотрудника',
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text='Уникальный идентификатор из HR-системы'
    )
    middle_name = models.CharField('Отчество', max_length=150, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    
    # Должность и подразделение
    position = models.ForeignKey(
        'org.Position',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name='Должность'
    )
    department = models.ForeignKey(
        'org.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name='Подразделение'
    )
    
    # Даты
    hire_date = models.DateField('Дата приёма', null=True, blank=True)
    termination_date = models.DateField('Дата увольнения', null=True, blank=True)
    
    # Рабочие контакты
    work_phone = models.CharField('Рабочий телефон', max_length=20, blank=True)
    work_email = models.EmailField('Рабочий email', blank=True)
    office_location = models.CharField('Расположение офиса', max_length=100, blank=True)
    
    # Грейд и категория
    band = models.CharField('Грейд (Band)', max_length=10, blank=True)
    employee_category = models.CharField('Категория сотрудника', max_length=50, blank=True)
    
    # Руководство
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        verbose_name='Руководитель'
    )
    hr_partner = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_employees',
        verbose_name='HR-партнёр'
    )
    
    # Синхронизация
    hr_synced_at = models.DateTimeField('Последняя синхронизация HR', null=True, blank=True)
    hr_external_data = models.JSONField('Дополнительные данные HR', null=True, blank=True)
    
    # === Редактируемые сотрудником данные ===
    avatar = models.ImageField(
        'Фото профиля',
        upload_to='avatars/',
        blank=True,
        null=True
    )
    personal_phone = models.CharField('Личный телефон', max_length=20, blank=True)
    personal_email = models.EmailField('Личный email', blank=True)
    
    # Мессенджеры
    telegram = models.CharField('Telegram', max_length=100, blank=True)
    whatsapp = models.CharField('WhatsApp', max_length=20, blank=True)
    
    # О себе
    about = models.TextField('О себе', blank=True)
    skills = models.JSONField('Навыки и компетенции', null=True, blank=True)
    
    # Настройки приватности
    show_birth_date = models.BooleanField('Показывать дату рождения', default=True)
    show_personal_phone = models.BooleanField('Показывать личный телефон', default=False)
    show_personal_email = models.BooleanField('Показывать личный email', default=False)
    
    # === Статус и замещение ===
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    status_end_date = models.DateField('Дата окончания статуса', null=True, blank=True)
    substitute = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='substituting_for',
        verbose_name='Замещающий'
    )
    
    # === Роли и права ===
    isModerator = models.BooleanField('Модератор', default=False)
    is_hr = models.BooleanField('HR-специалист', default=False)
    is_admin_portal = models.BooleanField('Администратор портала', default=False)
    
    # === Модерация комментариев ===
    comment_warnings = models.PositiveSmallIntegerField(
        'Предупреждения за комментарии',
        default=0,
        help_text='После 3 предупреждений блокируется возможность комментирования'
    )
    is_comments_banned = models.BooleanField(
        'Заблокирован для комментариев',
        default=False,
        help_text='Пользователь не может оставлять комментарии'
    )
    comments_banned_at = models.DateTimeField('Дата блокировки комментариев', null=True, blank=True)
    
    # === Служебные поля ===
    is_archived = models.BooleanField('Архивирован', default=False)
    archived_at = models.DateTimeField('Дата архивации', null=True, blank=True)
    archived_reason = models.CharField('Причина архивации', max_length=255, blank=True)
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['birth_date']),
            models.Index(fields=['status']),
            models.Index(fields=['department', 'is_active']),
            models.Index(fields=['manager']),
            models.Index(fields=['is_archived']),
        ]

    def __str__(self):
        return self.get_full_name() or self.username

    def get_full_name(self):
        """Полное имя с отчеством"""
        parts = [self.last_name, self.first_name, self.middle_name]
        return ' '.join(p for p in parts if p).strip()

    def get_short_name(self):
        """Краткое имя (Фамилия И.О.)"""
        parts = [self.last_name]
        if self.first_name:
            parts.append(f"{self.first_name[0]}.")
        if self.middle_name:
            parts.append(f"{self.middle_name[0]}.")
        return ' '.join(parts)

    def is_on_leave(self):
        """Проверка на отсутствие (отпуск/больничный и т.д.)"""
        return self.status in ['vacation', 'sick_leave', 'business_trip', 'maternity', 'unpaid_leave']

    def archive(self, reason: str = ''):
        """Архивировать сотрудника"""
        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_reason = reason
        self.is_active = False
        self.save(update_fields=['is_archived', 'archived_at', 'archived_reason', 'is_active'])

    def get_manager_chain(self):
        """Получить цепочку руководителей"""
        chain = []
        current = self.manager
        seen = set()
        while current and current.id not in seen:
            chain.append(current)
            seen.add(current.id)
            current = current.manager
        return chain


class EmployeeProject(models.Model):
    """
    Проекты сотрудника.
    Могут быть введены вручную или синхронизированы из проектной системы.
    """
    SOURCE_CHOICES = [
        ('manual', 'Вручную'),
        ('integration', 'Из проектной системы'),
    ]

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name='Сотрудник'
    )
    name = models.CharField('Название проекта', max_length=255)
    description = models.TextField('Описание', blank=True)
    role = models.CharField('Роль в проекте', max_length=100, blank=True)
    
    # Сроки
    start_date = models.DateField('Дата начала', null=True, blank=True)
    end_date = models.DateField('Дата окончания', null=True, blank=True)
    is_current = models.BooleanField('Текущий проект', default=True)
    
    # Внешняя система
    external_id = models.CharField('ID в проектной системе', max_length=100, null=True, blank=True)
    source = models.CharField('Источник', max_length=20, choices=SOURCE_CHOICES, default='manual')
    
    # Служебные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Проект сотрудника'
        verbose_name_plural = 'Проекты сотрудников'
        ordering = ['-is_current', '-start_date']

    def __str__(self):
        return f"{self.employee} - {self.name}"
