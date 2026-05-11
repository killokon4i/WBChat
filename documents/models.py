from django.db import models
from django.conf import settings
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.db.models import Q
import hashlib


class DocumentCategory(models.Model):
    """
    Категория/рубрика документов (иерархическая структура).
    Определяет тип документации и сроки хранения.
    """
    name = models.CharField('Название', max_length=255)
    slug = models.SlugField('Slug', unique=True)
    description = models.TextField('Описание', blank=True)
    
    # Иерархия
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )
    
    # Настройки
    retention_days = models.PositiveIntegerField(
        'Срок хранения (дней)',
        null=True,
        blank=True,
        help_text='Оставьте пустым для бессрочного хранения'
    )
    icon = models.CharField('Иконка', max_length=50, blank=True)
    color = models.CharField('Цвет', max_length=7, default='#CB11AB')
    
    # Служебные
    is_active = models.BooleanField('Активна', default=True)
    order = models.PositiveIntegerField('Порядок сортировки', default=0)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Категория документов'
        verbose_name_plural = 'Категории документов'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_full_path(self):
        """Получить полный путь категории"""
        parts = [self.name]
        parent = self.parent
        while parent:
            parts.insert(0, parent.name)
            parent = parent.parent
        return ' / '.join(parts)


class Document(models.Model):
    """
    Основная модель документа.
    Поддерживает НПА, регламенты, приказы и другие типы документов.
    """
    TYPES = [
        ('order', 'Приказ'),
        ('instruction', 'Указание'),
        ('regulation', 'Регламент'),
        ('policy', 'Политика'),
        ('letter', 'Письмо ЦБ'),
        ('memo', 'Служебная записка'),
        ('manual', 'Инструкция'),
        ('template', 'Шаблон'),
        ('other', 'Прочее'),
    ]
    
    CONFIDENTIALITY = [
        ('public', 'Общедоступный'),
        ('internal', 'Для служебного пользования'),
        ('confidential', 'Конфиденциально'),
        ('secret', 'Секретно'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('review', 'На согласовании'),
        ('active', 'Актуален'),
        ('outdated', 'Неактуален'),
        ('archived', 'В архиве'),
    ]

    # === Основные поля ===
    title = models.CharField('Название', max_length=500)
    document_type = models.CharField('Тип документа', max_length=20, choices=TYPES)
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.PROTECT,
        related_name='documents',
        verbose_name='Категория'
    )
    description = models.TextField('Описание', blank=True)
    
    # === Метаданные НПА ===
    document_number = models.CharField('Номер документа', max_length=100, blank=True)
    document_date = models.DateField('Дата документа', null=True, blank=True)
    effective_date = models.DateField('Дата вступления в силу', null=True, blank=True)
    expiry_date = models.DateField('Дата утраты силы', null=True, blank=True)
    basis = models.TextField('Основание', blank=True, help_text='На основании какого документа издан')
    confidentiality = models.CharField(
        'Гриф конфиденциальности',
        max_length=20,
        choices=CONFIDENTIALITY,
        default='internal'
    )
    
    # === Статус ===
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # === Ответственные ===
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='authored_documents',
        verbose_name='Автор'
    )
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='curated_documents',
        verbose_name='Куратор'
    )
    
    # === Внешние связи ===
    tezis_link = models.URLField('Ссылка в СЭД Тезис', blank=True)
    tezis_id = models.CharField('ID в Тезис', max_length=100, blank=True)
    
    # === Legal Hold ===
    is_legal_hold = models.BooleanField(
        'Legal Hold',
        default=False,
        help_text='Заморозка удаления при проверках/расследованиях'
    )
    legal_hold_reason = models.TextField('Причина Legal Hold', blank=True)
    legal_hold_until = models.DateField('Legal Hold до', null=True, blank=True)
    legal_hold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='legal_holds',
        verbose_name='Legal Hold установил'
    )
    
    # === Полнотекстовый поиск (PostgreSQL) ===
    search_vector = SearchVectorField('Поисковый вектор', null=True)
    
    # === Теги ===
    tags = models.JSONField('Теги', null=True, blank=True)
    
    # === Служебные ===
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    published_at = models.DateTimeField('Опубликовано', null=True, blank=True)
    views_count = models.PositiveIntegerField('Просмотров', default=0)

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-updated_at']
        indexes = [
            GinIndex(fields=['search_vector']),
            models.Index(fields=['document_number', 'document_date']),
            models.Index(fields=['status', 'document_type']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['confidentiality']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['document_number', 'document_date'],
                condition=Q(document_number__gt=''),
                name='unique_doc_number_date'
            )
        ]

    def __str__(self):
        if self.document_number:
            return f"{self.document_number} - {self.title}"
        return self.title

    def get_current_version(self):
        """Получить текущую версию документа"""
        return self.versions.order_by('-version_number').first()

    def can_be_deleted(self):
        """Проверка возможности удаления"""
        if self.is_legal_hold:
            return False, 'Документ находится под Legal Hold'
        return True, ''


class DocumentVersion(models.Model):
    """
    Версия документа.
    Хранит файл и метаданные о конкретной версии.
    """
    SCAN_RESULTS = [
        ('pending', 'Ожидает проверки'),
        ('clean', 'Чисто'),
        ('infected', 'Обнаружена угроза'),
        ('error', 'Ошибка проверки'),
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Документ'
    )
    version_number = models.PositiveIntegerField('Номер версии')
    
    # === Файл ===
    file = models.FileField('Файл', upload_to='documents/%Y/%m/')
    file_name = models.CharField('Имя файла', max_length=255)
    file_size = models.PositiveIntegerField('Размер файла (байт)')
    file_hash = models.CharField('SHA-256 хэш', max_length=64)
    mime_type = models.CharField('MIME тип', max_length=100)
    
    # === Безопасность ===
    is_scanned = models.BooleanField('Проверен антивирусом', default=False)
    scan_result = models.CharField(
        'Результат проверки',
        max_length=20,
        choices=SCAN_RESULTS,
        default='pending'
    )
    scan_date = models.DateTimeField('Дата проверки', null=True, blank=True)
    
    # === Превью ===
    preview_file = models.FileField('Превью (PDF)', upload_to='previews/%Y/%m/', null=True, blank=True)
    has_preview = models.BooleanField('Есть превью', default=False)
    
    # === Метаданные версии ===
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Загрузил'
    )
    uploaded_at = models.DateTimeField('Дата загрузки', auto_now_add=True)
    comment = models.TextField('Комментарий к версии', blank=True)
    
    # === Страницы (для PDF) ===
    page_count = models.PositiveIntegerField('Количество страниц', null=True, blank=True)

    class Meta:
        verbose_name = 'Версия документа'
        verbose_name_plural = 'Версии документов'
        ordering = ['-version_number']
        unique_together = ['document', 'version_number']

    def __str__(self):
        return f"{self.document} - v{self.version_number}"

    def save(self, *args, **kwargs):
        # Автоматический номер версии
        if not self.version_number:
            last = self.document.versions.order_by('-version_number').first()
            self.version_number = (last.version_number + 1) if last else 1
        
        # Вычисление хэша если файл новый
        if self.file and not self.file_hash:
            self.file_hash = self._calculate_hash()
        
        super().save(*args, **kwargs)

    def _calculate_hash(self):
        """Вычислить SHA-256 хэш файла"""
        sha256 = hashlib.sha256()
        for chunk in self.file.chunks():
            sha256.update(chunk)
        return sha256.hexdigest()


class DocumentAcknowledgement(models.Model):
    """
    Ознакомление с документом.
    Отслеживает кто и когда ознакомился с документом.
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='acknowledgements',
        verbose_name='Документ'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_acknowledgements',
        verbose_name='Сотрудник'
    )
    
    # Обязательность
    required = models.BooleanField('Обязательно', default=True)
    deadline = models.DateTimeField('Срок ознакомления', null=True, blank=True)
    
    # Статус
    acknowledged_at = models.DateTimeField('Ознакомлен', null=True, blank=True)
    acknowledged_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Версия ознакомления'
    )
    
    # Напоминания
    reminder_sent = models.BooleanField('Напоминание отправлено', default=False)
    reminder_sent_at = models.DateTimeField('Дата напоминания', null=True, blank=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Ознакомление с документом'
        verbose_name_plural = 'Ознакомления с документами'
        unique_together = ['document', 'user']
        indexes = [
            models.Index(fields=['user', 'acknowledged_at']),
            models.Index(fields=['document', 'required', 'acknowledged_at']),
        ]

    def __str__(self):
        status = 'Ознакомлен' if self.acknowledged_at else 'Ожидает'
        return f"{self.user} - {self.document} ({status})"


class DocumentAccessRule(models.Model):
    """
    Правила доступа к документам (RBAC/ABAC).
    Определяет кто и какие действия может выполнять с документами.
    """
    PERMISSION_TYPES = [
        ('view', 'Просмотр'),
        ('download', 'Скачивание'),
        ('edit', 'Редактирование'),
        ('delete', 'Удаление'),
        ('publish', 'Публикация'),
        ('manage_access', 'Управление доступом'),
    ]

    # К чему применяется (один из вариантов)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='access_rules',
        verbose_name='Документ'
    )
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='access_rules',
        verbose_name='Категория'
    )
    
    # Кому доступ (один из вариантов)
    role = models.CharField('Роль', max_length=50, blank=True)
    department = models.ForeignKey(
        'org.Department',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='document_access_rules',
        verbose_name='Подразделение'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='document_access_rules',
        verbose_name='Пользователь'
    )
    
    # Уровень конфиденциальности
    min_confidentiality = models.CharField(
        'Минимальный гриф',
        max_length=20,
        choices=Document.CONFIDENTIALITY,
        blank=True
    )
    
    # Разрешения
    can_view = models.BooleanField('Просмотр', default=False)
    can_download = models.BooleanField('Скачивание', default=False)
    can_edit = models.BooleanField('Редактирование', default=False)
    can_delete = models.BooleanField('Удаление', default=False)
    can_publish = models.BooleanField('Публикация', default=False)
    can_manage_access = models.BooleanField('Управление доступом', default=False)
    
    # Служебные
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_access_rules',
        verbose_name='Создал'
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Правило доступа к документу'
        verbose_name_plural = 'Правила доступа к документам'

    def __str__(self):
        target = self.document or self.category or 'Все'
        subject = self.user or self.department or self.role or 'Все'
        return f"{subject} -> {target}"


class DocumentViewLog(models.Model):
    """Журнал просмотров документов"""
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='view_logs',
        verbose_name='Документ'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_views',
        verbose_name='Пользователь'
    )
    version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Версия'
    )
    viewed_at = models.DateTimeField('Время просмотра', auto_now_add=True)
    ip_address = models.GenericIPAddressField('IP адрес', null=True, blank=True)

    class Meta:
        verbose_name = 'Просмотр документа'
        verbose_name_plural = 'Журнал просмотров'
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['document', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
        ]


