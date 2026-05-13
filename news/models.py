from django.db import models
from django.conf import settings
from django.utils import timezone


class NewsCategory(models.Model):
    """
    Рубрика/категория новостей.
    Позволяет классифицировать новости по типам.
    """
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('Slug', unique=True)
    description = models.TextField('Описание', blank=True)
    color = models.CharField('Цвет', max_length=7, default='#ff2fb3')
    icon = models.CharField('Иконка', max_length=50, blank=True)
    
    # Характеристики
    is_official = models.BooleanField(
        'Официальная',
        default=False,
        help_text='Официальные приказы, распоряжения'
    )
    requires_moderation = models.BooleanField('Требует модерации', default=True)
    
    # Порядок
    order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активна', default=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Рубрика новостей'
        verbose_name_plural = 'Рубрики новостей'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class News(models.Model):
    """
    Корпоративная новость/объявление.
    Расширенная модель с поддержкой рубрик, модерации и видимости.
    """
    VISIBILITY_CHOICES = [
        ('all', 'Все сотрудники'),
        ('department', 'По подразделению'),
        ('selected', 'Выбранные сотрудники'),
    ]
    
    MODERATION_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    # === Основное ===
    title = models.CharField('Заголовок', max_length=255)
    slug = models.SlugField('Slug', blank=True, max_length=255)
    content = models.TextField('Содержимое')
    excerpt = models.TextField('Краткое описание', blank=True, max_length=500)
    
    # Категория
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='news',
        verbose_name='Рубрика'
    )
    
    # Изображение
    image = models.ImageField('Обложка', upload_to='news_images/', blank=True, null=True)
    
    # Автор
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='news_posts',
        verbose_name='Автор'
    )
    
    # === Закрепление ===
    is_pinned = models.BooleanField('Закреплено', default=False)
    pin_until = models.DateTimeField('Закреплено до', null=True, blank=True)
    pin_order = models.PositiveIntegerField('Порядок закрепления', default=0)
    
    # === Комментарии ===
    allow_comments = models.BooleanField('Разрешить комментарии', default=True)
    comments_count = models.PositiveIntegerField('Количество комментариев', default=0)
    
    # === Видимость ===
    visibility = models.CharField(
        'Видимость',
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='all'
    )
    visible_to_departments = models.ManyToManyField(
        'org.Department',
        blank=True,
        related_name='visible_news',
        verbose_name='Доступно подразделениям'
    )
    visible_to_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='accessible_news',
        verbose_name='Доступно сотрудникам'
    )
    
    # === Модерация ===
    moderation_status = models.CharField(
        'Статус модерации',
        max_length=20,
        choices=MODERATION_CHOICES,
        default='approved'
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_news',
        verbose_name='Модератор'
    )
    moderated_at = models.DateTimeField('Дата модерации', null=True, blank=True)
    moderation_comment = models.TextField('Комментарий модератора', blank=True)
    
    # === Статистика ===
    views_count = models.PositiveIntegerField('Просмотров', default=0)
    
    # === Публикация ===
    is_published = models.BooleanField('Опубликовано', default=False)
    published_at = models.DateTimeField('Дата публикации', null=True, blank=True)
    schedule_publish_at = models.DateTimeField('Запланировать публикацию', null=True, blank=True)
    
    # === Служебные ===
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-is_pinned', '-pin_order', '-published_at', '-created_at']
        indexes = [
            models.Index(fields=['-is_pinned', '-published_at']),
            models.Index(fields=['category', '-published_at']),
            models.Index(fields=['moderation_status', '-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Автоматическое заполнение excerpt
        if not self.excerpt and self.content:
            self.excerpt = self.content[:497] + '...' if len(self.content) > 500 else self.content
        
        # Публикация
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)

    def recompute_comments_count(self):
        """
        Пересчитать количество комментариев с учётом мягкого удаления.
        Считаем все комментарии (включая ответы), где is_deleted = False.
        """
        count = self.comments.filter(is_deleted=False).count()
        self.comments_count = count
        self.save(update_fields=['comments_count'])

    def is_visible_to_user(self, user):
        """Проверка видимости для пользователя"""
        if self.visibility == 'all':
            return True
        elif self.visibility == 'department':
            if user.department:
                return self.visible_to_departments.filter(id=user.department.id).exists()
            return False
        elif self.visibility == 'selected':
            return self.visible_to_users.filter(id=user.id).exists()
        return False


class NewsAttachment(models.Model):
    """
    Вложения к новости.
    Поддерживает изображения, видео и документы.
    """
    FILE_TYPES = [
        ('image', 'Изображение'),
        ('video', 'Видео'),
        ('document', 'Документ'),
        ('other', 'Другое'),
    ]

    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='Новость'
    )
    file = models.FileField('Файл', upload_to='news_attachments/%Y/%m/')
    file_name = models.CharField('Имя файла', max_length=255)
    file_type = models.CharField('Тип файла', max_length=20, choices=FILE_TYPES, default='other')
    file_size = models.PositiveIntegerField('Размер (байт)', default=0)
    
    # Для изображений/видео
    width = models.PositiveIntegerField('Ширина', null=True, blank=True)
    height = models.PositiveIntegerField('Высота', null=True, blank=True)
    duration = models.PositiveIntegerField('Длительность (сек)', null=True, blank=True)
    
    # Превью
    thumbnail = models.ImageField('Превью', upload_to='news_thumbnails/%Y/%m/', null=True, blank=True)
    
    # Порядок
    order = models.PositiveIntegerField('Порядок', default=0)
    
    uploaded_at = models.DateTimeField('Загружено', auto_now_add=True)

    class Meta:
        verbose_name = 'Вложение новости'
        verbose_name_plural = 'Вложения новостей'
        ordering = ['order', 'uploaded_at']

    def __str__(self):
        return self.file_name


class NewsComment(models.Model):
    """
    Комментарии к новостям.
    Поддерживает древовидную структуру и упоминания.
    """
    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Новость'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='news_comments',
        verbose_name='Автор'
    )
    content = models.TextField('Содержимое')
    
    # Древовидная структура
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Родительский комментарий'
    )
    level = models.PositiveSmallIntegerField('Уровень вложенности', default=0)
    
    # Упоминания
    mentions = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='mentioned_in_news_comments',
        verbose_name='Упоминания'
    )
    
    # Статусы
    is_edited = models.BooleanField('Отредактировано', default=False)
    edited_at = models.DateTimeField('Дата редактирования', null=True, blank=True)
    is_deleted = models.BooleanField('Удалено', default=False)
    deleted_at = models.DateTimeField('Дата удаления', null=True, blank=True)
    
    # Модерация
    is_hidden = models.BooleanField('Скрыто модератором', default=False)
    hidden_reason = models.CharField('Причина скрытия', max_length=255, blank=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['news', 'created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['parent', 'created_at']),
        ]

    def __str__(self):
        return f"{self.author} - {self.content[:50]}"

    def save(self, *args, **kwargs):
        # Вычисляем уровень вложенности
        if self.parent:
            self.level = self.parent.level + 1
        super().save(*args, **kwargs)

    def soft_delete(self):
        """Мягкое удаление"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.content = '[Комментарий удалён]'
        self.save(update_fields=['is_deleted', 'deleted_at', 'content'])
        # Обновляем счётчик комментариев у новости
        if self.news_id:
            self.news.recompute_comments_count()


class NewsReaction(models.Model):
    """
    Реакции на новости.
    Поддерживает различные эмодзи-реакции.
    """
    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name='reactions',
        verbose_name='Новость'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='news_reactions',
        verbose_name='Пользователь'
    )
    emoji = models.CharField('Эмодзи', max_length=10)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Реакция на новость'
        verbose_name_plural = 'Реакции на новости'
        unique_together = ['news', 'user']  # Один юзер = одна реакция
        indexes = [
            models.Index(fields=['news', 'emoji']),
        ]

    def __str__(self):
        return f"{self.user} - {self.emoji} - {self.news}"


class NewsEditLog(models.Model):
    """
    Журнал правок новости.
    Отслеживает все изменения для аудита.
    """
    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name='edit_logs',
        verbose_name='Новость'
    )
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Редактор'
    )
    field_name = models.CharField('Поле', max_length=100)
    old_value = models.TextField('Старое значение', blank=True)
    new_value = models.TextField('Новое значение', blank=True)
    edited_at = models.DateTimeField('Дата изменения', auto_now_add=True)

    class Meta:
        verbose_name = 'Запись изменения новости'
        verbose_name_plural = 'Журнал изменений новостей'
        ordering = ['-edited_at']

    def __str__(self):
        return f"{self.news} - {self.field_name} ({self.edited_at})"


class NewsView(models.Model):
    """
    Просмотры новостей.
    Отслеживает кто и когда просматривал новость.
    """
    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name='views',
        verbose_name='Новость'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='news_views',
        verbose_name='Пользователь'
    )
    viewed_at = models.DateTimeField('Время просмотра', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Просмотр новости'
        verbose_name_plural = 'Просмотры новостей'
        indexes = [
            models.Index(fields=['news', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
        ]
