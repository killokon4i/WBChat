from django.db import models
from django.conf import settings
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone
from django.utils.text import slugify
import re


class Category(models.Model):
    """Иерархические рубрики Базы знаний (IT, HR, Продукты Банка, Новичку...)"""
    name = models.CharField('Название', max_length=255)
    slug = models.SlugField('Slug', unique=True, max_length=255)
    description = models.TextField('Описание', blank=True)
    icon = models.CharField('Иконка (emoji/css)', max_length=50, blank=True)
    color = models.CharField('Цвет', max_length=7, default='#ff2fb3')

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='children',
        verbose_name='Родительская рубрика'
    )
    level = models.PositiveIntegerField('Уровень вложенности', default=0)
    path = models.CharField('Materialized Path', max_length=1000, blank=True, db_index=True)

    order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активна', default=True)

    is_restricted = models.BooleanField(
        'Ограниченный доступ', default=False,
        help_text='Видна только указанным подразделениям/ролям'
    )
    allowed_departments = models.ManyToManyField(
        'org.Department', blank=True,
        related_name='kb_categories',
        verbose_name='Доступные подразделения'
    )
    allowed_roles = models.JSONField(
        'Разрешённые роли', null=True, blank=True,
        help_text='["is_hr", "isModerator", ...]'
    )

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Рубрика'
        verbose_name_plural = 'Рубрики'
        ordering = ['path', 'order', 'name']
        indexes = [
            models.Index(fields=['path']),
            models.Index(fields=['parent', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.parent:
            self.level = self.parent.level + 1
            self.path = f"{self.parent.path}/{self.slug}" if self.parent.path else self.slug
        else:
            self.level = 0
            self.path = self.slug
        super().save(*args, **kwargs)

    def get_ancestors(self):
        if not self.parent:
            return Category.objects.none()
        slugs = self.path.split('/')[:-1]
        return Category.objects.filter(slug__in=slugs).order_by('level')

    def get_descendants(self):
        return Category.objects.filter(path__startswith=f"{self.path}/")

    def get_breadcrumbs(self):
        ancestors = list(self.get_ancestors())
        ancestors.append(self)
        return ancestors

    def is_visible_to(self, user):
        if not self.is_restricted:
            return True
        if user.is_superuser or getattr(user, 'is_admin_portal', False):
            return True
        if self.allowed_departments.filter(id=getattr(user.department, 'id', None)).exists():
            return True
        if self.allowed_roles:
            for role in self.allowed_roles:
                if getattr(user, role, False):
                    return True
        return False


class Tag(models.Model):
    """Теги для гибкой навигации (#VPN, #Обучение, ...)"""
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Slug', unique=True, max_length=100)
    description = models.TextField('Описание', blank=True)
    synonyms = models.JSONField(
        'Синонимы/акронимы', null=True, blank=True,
        help_text='["ДБО", "дистанционное банковское обслуживание"]'
    )
    usage_count = models.PositiveIntegerField('Использований', default=0)
    is_controlled = models.BooleanField('Контролируемый словарь', default=False)
    is_approved = models.BooleanField('Одобрен', default=True)

    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class ArticleTemplate(models.Model):
    """Шаблоны для разных типов статей (How-to, FAQ, Политика...)"""
    TYPE_CHOICES = [
        ('howto', 'How-to'),
        ('procedure', 'Процедура/SOP'),
        ('policy', 'Политика'),
        ('troubleshooting', 'Траблшутинг'),
        ('faq', 'FAQ'),
        ('checklist', 'Чек-лист'),
        ('onboarding', 'Онбординг'),
    ]

    name = models.CharField('Название шаблона', max_length=255)
    article_type = models.CharField('Тип статьи', max_length=20, choices=TYPE_CHOICES)
    content_template = models.TextField('HTML-заготовка контента')
    checklist = models.JSONField(
        'Чек-лист качества', null=True, blank=True,
        help_text='["Проверить битые ссылки", "Добавить alt к изображениям", ...]'
    )
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Шаблон статьи'
        verbose_name_plural = 'Шаблоны статей'

    def __str__(self):
        return self.name


class Article(models.Model):
    """Основная модель статьи Базы знаний"""
    TYPE_CHOICES = ArticleTemplate.TYPE_CHOICES
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('review', 'На проверке'),
        ('published', 'Опубликовано'),
        ('needs_review', 'На пересмотре'),
        ('archived', 'Архив'),
    ]

    title = models.CharField('Заголовок', max_length=500)
    slug = models.SlugField('Slug', unique=True, max_length=500, blank=True)
    content = models.TextField('Содержимое (HTML)')
    excerpt = models.TextField('Краткое описание', blank=True, max_length=10000)
    article_type = models.CharField('Тип', max_length=20, choices=TYPE_CHOICES, default='howto')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='articles',
        verbose_name='Рубрика'
    )
    categories = models.ManyToManyField(
        Category, blank=True,
        related_name='cross_articles',
        verbose_name='Доп. рубрики (кросс-категории)'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles', verbose_name='Теги')

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='kb_articles',
        verbose_name='Автор'
    )
    editors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='kb_editable_articles',
        verbose_name='Редакторы'
    )

    template = models.ForeignKey(
        ArticleTemplate, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Шаблон'
    )

    related_documents = models.ManyToManyField(
        'documents.Document', blank=True,
        related_name='kb_articles',
        verbose_name='Связанные НПА'
    )
    needs_actualization = models.BooleanField(
        'Требует актуализации', default=False,
        help_text='Авто-флаг при изменении связанного НПА'
    )

    review_period_months = models.PositiveSmallIntegerField(
        'Период пересмотра (мес.)', default=12
    )
    next_review_date = models.DateField('Дата следующего пересмотра', null=True, blank=True)
    last_reviewed_at = models.DateTimeField('Последний пересмотр', null=True, blank=True)
    last_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='kb_reviewed_articles',
        verbose_name='Пересмотрел'
    )

    search_vector = SearchVectorField('Поисковый вектор', null=True)

    views_count = models.PositiveIntegerField('Просмотров', default=0)
    avg_rating = models.FloatField('Средний рейтинг', default=0)
    ratings_count = models.PositiveIntegerField('Количество оценок', default=0)
    comments_count = models.PositiveIntegerField('Комментариев', default=0)

    is_pinned = models.BooleanField('Закреплено', default=False)
    published_at = models.DateTimeField('Дата публикации', null=True, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    current_version = models.PositiveIntegerField('Текущая версия', default=1)

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-is_pinned', '-published_at', '-created_at']
        indexes = [
            GinIndex(fields=['search_vector']),
            models.Index(fields=['status', '-published_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['article_type', 'status']),
            models.Index(fields=['next_review_date']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or f'article-{timezone.now().timestamp():.0f}'
            slug = base[:490]
            counter = 1
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base[:480]}-{counter}"
                counter += 1
            self.slug = slug

        if not self.excerpt and self.content:
            clean = re.sub(r'<[^>]+>', '', self.content)
            self.excerpt = clean[:9997] + '...' if len(clean) > 10000 else clean

        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()

        if self.status == 'published' and not self.next_review_date:
            from datetime import timedelta
            base_date = self.published_at or timezone.now()
            self.next_review_date = (base_date + timedelta(days=30 * self.review_period_months)).date()

        super().save(*args, **kwargs)

    def can_edit(self, user):
        if user.is_superuser or getattr(user, 'is_admin_portal', False):
            return True
        if getattr(user, 'isModerator', False):
            return True
        if self.author_id == user.id:
            return True
        if self.editors.filter(id=user.id).exists():
            return True
        return False

    def can_view(self, user):
        if self.status == 'published':
            if self.category and not self.category.is_visible_to(user):
                return False
            return True
        return self.can_edit(user)

    def get_breadcrumbs(self):
        if self.category:
            return self.category.get_breadcrumbs()
        return []

    def generate_toc(self):
        """Генерация оглавления по H2/H3"""
        pattern = re.compile(r'<(h[23])([^>]*)>(.*?)</\1>', re.IGNORECASE | re.DOTALL)
        toc = []
        used_anchors = set()
        for match in pattern.finditer(self.content):
            tag = match.group(1).lower()
            text = re.sub(r'<[^>]+>', '', match.group(3)).strip()
            anchor = slugify(text, allow_unicode=True) or f'section-{len(toc)}'
            base_anchor = anchor
            counter = 1
            while anchor in used_anchors:
                anchor = f'{base_anchor}-{counter}'
                counter += 1
            used_anchors.add(anchor)
            toc.append({'tag': tag, 'text': text, 'anchor': anchor, 'level': int(tag[1])})
        return toc

    def content_with_anchors(self):
        """Контент с id-якорями на заголовках — каждый получает уникальный id"""
        toc = self.generate_toc()
        toc_iter = iter(toc)

        def _replacer(match):
            try:
                item = next(toc_iter)
            except StopIteration:
                return match.group(0)
            tag = match.group(1)
            attrs = match.group(2)
            inner = match.group(3)
            if 'id=' in attrs:
                return match.group(0)
            return f'<{tag}{attrs} id="{item["anchor"]}">{inner}</{tag}>'

        pattern = re.compile(r'<(h[23])([^>]*)>(.*?)</\1>', re.IGNORECASE | re.DOTALL)
        return pattern.sub(_replacer, self.content)


class ArticleVersion(models.Model):
    """Версия статьи — хранит историю изменений"""
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Статья'
    )
    version_number = models.PositiveIntegerField('Номер версии')
    title = models.CharField('Заголовок', max_length=500)
    content = models.TextField('Содержимое')

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Автор правки'
    )
    comment = models.CharField('Описание изменений', max_length=500, blank=True)
    is_rollback = models.BooleanField('Откат', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Версия статьи'
        verbose_name_plural = 'Версии статей'
        ordering = ['-version_number']
        unique_together = ['article', 'version_number']

    def __str__(self):
        return f"{self.article.title} — v{self.version_number}"


class ArticleAttachment(models.Model):
    """Вложения к статье"""
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='Статья'
    )
    file = models.FileField('Файл', upload_to='kb/attachments/%Y/%m/')
    file_name = models.CharField('Имя файла', max_length=255)
    file_size = models.PositiveIntegerField('Размер (байт)', default=0)
    mime_type = models.CharField('MIME', max_length=100, blank=True)
    thumbnail = models.ImageField('Миниатюра', upload_to='kb/thumbnails/', blank=True, null=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Загрузил'
    )
    uploaded_at = models.DateTimeField('Загружено', auto_now_add=True)

    class Meta:
        verbose_name = 'Вложение'
        verbose_name_plural = 'Вложения'

    def __str__(self):
        return self.file_name


class ArticleComment(models.Model):
    """Комментарии к статьям с поддержкой вложенности и @mentions"""
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='article_comments',
        verbose_name='Статья'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='kb_comments',
        verbose_name='Автор'
    )
    content = models.TextField('Текст')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='replies',
        verbose_name='Ответ на'
    )

    is_deleted = models.BooleanField('Удалён', default=False)
    is_edited = models.BooleanField('Изменён', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author} — {self.content[:50]}"


class ArticleRating(models.Model):
    """Оценка статьи (1-5 звёзд)"""
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name='Статья'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='kb_ratings',
        verbose_name='Пользователь'
    )
    score = models.PositiveSmallIntegerField('Оценка', help_text='1-5')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Оценка статьи'
        verbose_name_plural = 'Оценки статей'
        unique_together = ['article', 'user']

    def __str__(self):
        return f"{self.user} → {self.article}: {self.score}★"


class ArticleView(models.Model):
    """Просмотры статей для аналитики"""
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='article_views',
        verbose_name='Статья'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='kb_views',
        verbose_name='Пользователь'
    )
    viewed_at = models.DateTimeField('Время', auto_now_add=True)
    time_spent_seconds = models.PositiveIntegerField('Время на странице (сек)', default=0)
    ip_address = models.GenericIPAddressField('IP', null=True, blank=True)

    class Meta:
        verbose_name = 'Просмотр'
        verbose_name_plural = 'Просмотры'
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['article', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
        ]


class Subscription(models.Model):
    """Подписка на рубрики, теги или конкретные статьи"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='kb_subscriptions',
        verbose_name='Пользователь'
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='subscribers',
        verbose_name='Рубрика'
    )
    tag = models.ForeignKey(
        Tag, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='subscribers',
        verbose_name='Тег'
    )
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='subscribers',
        verbose_name='Статья'
    )

    notify_on_create = models.BooleanField('При создании', default=True)
    notify_on_update = models.BooleanField('При обновлении', default=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        target = self.category or self.tag or self.article or '?'
        return f"{self.user} → {target}"


class FAQ(models.Model):
    """Быстрые вопросы-ответы"""
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='faqs',
        verbose_name='Рубрика'
    )
    question = models.CharField('Вопрос', max_length=500)
    answer = models.TextField('Ответ (HTML)')
    related_article = models.ForeignKey(
        Article, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='faqs',
        verbose_name='Полная статья'
    )

    helpful_yes = models.PositiveIntegerField('Помогло', default=0)
    helpful_no = models.PositiveIntegerField('Не помогло', default=0)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Автор'
    )
    order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'
        ordering = ['category', 'order']

    def __str__(self):
        return self.question[:80]


class Snippet(models.Model):
    """Переиспользуемые фрагменты контента (контакты, версии ПО...)"""
    key = models.CharField('Ключ', max_length=100, unique=True)
    title = models.CharField('Название', max_length=255)
    content = models.TextField('Содержимое (HTML)')
    variables = models.JSONField(
        'Переменные', null=True, blank=True,
        help_text='{"version": "2.5.1", "support_email": "help@bank.ru"}'
    )
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Сниппет'
        verbose_name_plural = 'Сниппеты'

    def __str__(self):
        return self.title

    def render(self):
        result = self.content
        if self.variables:
            for k, v in self.variables.items():
                result = result.replace(f'{{{{{k}}}}}', str(v))
        return result


class EditLock(models.Model):
    """Мягкая блокировка при редактировании"""
    article = models.OneToOneField(
        Article, on_delete=models.CASCADE,
        related_name='edit_lock',
        verbose_name='Статья'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name='Редактор'
    )
    locked_at = models.DateTimeField('Заблокировано', auto_now_add=True)
    expires_at = models.DateTimeField('Истекает')

    class Meta:
        verbose_name = 'Блокировка редактирования'
        verbose_name_plural = 'Блокировки редактирования'

    def __str__(self):
        return f"{self.article} — {self.user}"

    def is_active(self):
        return self.expires_at > timezone.now()

    @classmethod
    def acquire(cls, article, user, duration_minutes=15):
        lock, created = cls.objects.get_or_create(
            article=article,
            defaults={
                'user': user,
                'expires_at': timezone.now() + timezone.timedelta(minutes=duration_minutes)
            }
        )
        if not created:
            if not lock.is_active() or lock.user == user:
                lock.user = user
                lock.locked_at = timezone.now()
                lock.expires_at = timezone.now() + timezone.timedelta(minutes=duration_minutes)
                lock.save()
                return lock, True
            return lock, False
        return lock, True

    @classmethod
    def release(cls, article, user):
        cls.objects.filter(article=article, user=user).delete()


class SearchQuery(models.Model):
    """Лог поисковых запросов для аналитики"""
    query = models.CharField('Запрос', max_length=500)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    results_count = models.PositiveIntegerField('Результатов', default=0)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Поисковый запрос'
        verbose_name_plural = 'Поисковые запросы'
        ordering = ['-created_at']


class SuggestedEdit(models.Model):
    """Предложение правки от пользователя без изменения оригинала"""
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('accepted', 'Принято'),
        ('rejected', 'Отклонено'),
    ]
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='suggested_edits',
        verbose_name='Статья'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='kb_suggested_edits',
        verbose_name='Автор предложения'
    )
    title = models.CharField('Предложенный заголовок', max_length=500, blank=True)
    content = models.TextField('Предложенный контент')
    comment = models.CharField('Комментарий к правке', max_length=500, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='kb_reviewed_suggestions',
        verbose_name='Рассмотрел'
    )
    review_comment = models.CharField('Комментарий модератора', max_length=500, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    reviewed_at = models.DateTimeField('Рассмотрено', null=True, blank=True)

    class Meta:
        verbose_name = 'Предложенная правка'
        verbose_name_plural = 'Предложенные правки'
        ordering = ['-created_at']

    def __str__(self):
        return f"Правка к «{self.article.title}» от {self.author}"


class TermRequest(models.Model):
    """Заявка на добавление нового термина/тега в контролируемый словарь"""
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]
    term = models.CharField('Термин', max_length=200)
    description = models.TextField('Описание / обоснование', blank=True)
    synonyms = models.CharField('Синонимы', max_length=500, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='kb_term_requests',
        verbose_name='Заявитель'
    )
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='kb_reviewed_terms',
        verbose_name='Рассмотрел'
    )
    created_tag = models.ForeignKey(
        Tag, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Созданный тег'
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    reviewed_at = models.DateTimeField('Рассмотрено', null=True, blank=True)

    class Meta:
        verbose_name = 'Заявка на термин'
        verbose_name_plural = 'Заявки на термины'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка: {self.term}"


class AuditLog(models.Model):
    """Журнал аудита доступа к статьям"""
    ACTION_CHOICES = [
        ('view', 'Просмотр'),
        ('download', 'Скачивание'),
        ('edit', 'Редактирование'),
        ('delete', 'Удаление'),
        ('publish', 'Публикация'),
        ('rollback', 'Откат версии'),
    ]
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name='Статья'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Пользователь'
    )
    action = models.CharField('Действие', max_length=20, choices=ACTION_CHOICES)
    details = models.TextField('Детали', blank=True)
    ip_address = models.GenericIPAddressField('IP', null=True, blank=True)
    created_at = models.DateTimeField('Время', auto_now_add=True)

    class Meta:
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['article', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_action_display()}: {self.article} — {self.user}"
