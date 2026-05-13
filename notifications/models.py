from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class NotificationChannel(models.Model):
    """
    Каналы доставки уведомлений.
    Определяет способы отправки уведомлений пользователям.
    """
    code = models.CharField('Код', max_length=20, unique=True)
    name = models.CharField('Название', max_length=100)
    description = models.TextField('Описание', blank=True)
    icon = models.CharField('Иконка', max_length=50, blank=True)
    
    # Настройки
    is_active = models.BooleanField('Активен', default=True)
    requires_confirmation = models.BooleanField(
        'Требует подтверждения',
        default=False,
        help_text='Например, подтверждение email'
    )
    
    # Порядок
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Канал уведомлений'
        verbose_name_plural = 'Каналы уведомлений'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class NotificationType(models.Model):
    """
    Типы уведомлений.
    Определяет категории уведомлений и их поведение по умолчанию.
    """
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]

    code = models.CharField('Код', max_length=50, unique=True)
    name = models.CharField('Название', max_length=100)
    description = models.TextField('Описание', blank=True)
    category = models.CharField('Категория', max_length=50, blank=True)
    icon = models.CharField('Иконка', max_length=50, blank=True)
    color = models.CharField('Цвет', max_length=7, default='#ff2fb3')
    
    # Каналы по умолчанию
    default_channels = models.ManyToManyField(
        NotificationChannel,
        blank=True,
        verbose_name='Каналы по умолчанию'
    )
    
    # Приоритет
    priority = models.CharField(
        'Приоритет по умолчанию',
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal'
    )
    
    # Шаблоны
    title_template = models.CharField(
        'Шаблон заголовка',
        max_length=255,
        help_text='Поддерживает {переменные}'
    )
    body_template = models.TextField(
        'Шаблон текста',
        help_text='Поддерживает {переменные}'
    )
    email_template = models.TextField('Шаблон email', blank=True)
    
    # Настройки
    is_active = models.BooleanField('Активен', default=True)
    can_be_disabled = models.BooleanField(
        'Можно отключить',
        default=True,
        help_text='Может ли пользователь отключить этот тип уведомлений'
    )
    
    # Группировка
    group_similar = models.BooleanField(
        'Группировать похожие',
        default=False,
        help_text='Группировать несколько однотипных уведомлений'
    )
    group_interval_minutes = models.PositiveIntegerField(
        'Интервал группировки (минуты)',
        default=60
    )

    class Meta:
        verbose_name = 'Тип уведомления'
        verbose_name_plural = 'Типы уведомлений'
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class Notification(models.Model):
    """
    Уведомление пользователю.
    Основная модель для хранения и отображения уведомлений.
    """
    PRIORITY_CHOICES = NotificationType.PRIORITY_CHOICES

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_notifications',
        verbose_name='Пользователь'
    )
    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Тип'
    )
    
    # Контент
    title = models.CharField('Заголовок', max_length=255)
    content = models.TextField('Содержимое')
    link = models.CharField('Ссылка', max_length=500, blank=True)
    
    # Связанный объект (Generic Foreign Key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Тип объекта'
    )
    object_id = models.PositiveIntegerField('ID объекта', null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Приоритет
    priority = models.CharField(
        'Приоритет',
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal'
    )
    
    # Статусы
    is_read = models.BooleanField('Прочитано', default=False)
    read_at = models.DateTimeField('Время прочтения', null=True, blank=True)
    
    # Доставка
    is_sent_email = models.BooleanField('Отправлено на email', default=False)
    is_sent_push = models.BooleanField('Отправлено push', default=False)
    
    # Служебные
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    expires_at = models.DateTimeField('Истекает', null=True, blank=True)
    
    # Группировка
    group_key = models.CharField('Ключ группировки', max_length=100, blank=True, db_index=True)
    grouped_count = models.PositiveIntegerField('Количество в группе', default=1)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['group_key', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user} - {self.title}"

    def mark_as_read(self):
        """Отметить как прочитанное"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class UserNotificationSettings(models.Model):
    """
    Настройки уведомлений пользователя.
    Позволяет настроить каналы и частоту для каждого типа уведомлений.
    """
    FREQUENCY_CHOICES = [
        ('instant', 'Мгновенно'),
        ('hourly', 'Раз в час'),
        ('daily', 'Раз в день'),
        ('weekly', 'Раз в неделю'),
        ('never', 'Никогда'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name='Пользователь'
    )
    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        related_name='user_settings',
        verbose_name='Тип уведомления'
    )
    
    # Настройки по каналам
    in_app_enabled = models.BooleanField('В приложении', default=True)
    email_enabled = models.BooleanField('Email', default=True)
    push_enabled = models.BooleanField('Push', default=True)
    
    # Частота
    email_frequency = models.CharField(
        'Частота email',
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='instant'
    )
    
    # Расписание (для digest)
    digest_time = models.TimeField('Время дайджеста', null=True, blank=True)
    digest_day = models.PositiveSmallIntegerField(
        'День недели для дайджеста',
        null=True,
        blank=True,
        help_text='0=Пн, 6=Вс'
    )

    class Meta:
        verbose_name = 'Настройка уведомлений пользователя'
        verbose_name_plural = 'Настройки уведомлений пользователей'
        unique_together = ['user', 'notification_type']

    def __str__(self):
        return f"{self.user} - {self.notification_type}"


class NotificationDeliveryLog(models.Model):
    """
    Журнал доставки уведомлений.
    Отслеживает попытки отправки по разным каналам.
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('sent', 'Отправлено'),
        ('delivered', 'Доставлено'),
        ('failed', 'Ошибка'),
        ('skipped', 'Пропущено'),
    ]

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='delivery_logs',
        verbose_name='Уведомление'
    )
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE,
        verbose_name='Канал'
    )
    
    # Статус
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Детали
    sent_at = models.DateTimeField('Отправлено', null=True, blank=True)
    delivered_at = models.DateTimeField('Доставлено', null=True, blank=True)
    error_message = models.TextField('Сообщение об ошибке', blank=True)
    
    # Внешние ID
    external_id = models.CharField('Внешний ID', max_length=255, blank=True)
    
    # Попытки
    attempts = models.PositiveSmallIntegerField('Попыток', default=0)
    next_retry_at = models.DateTimeField('Следующая попытка', null=True, blank=True)

    class Meta:
        verbose_name = 'Запись доставки уведомления'
        verbose_name_plural = 'Журнал доставки уведомлений'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.notification} -> {self.channel} ({self.status})"


