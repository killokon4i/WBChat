from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator


class Conversation(models.Model):
    """
    Represents a conversation (direct message, group chat, or channel).
    """
    CONVERSATION_TYPES = [
        ('direct', 'Direct Message'),
        ('group', 'Group Chat'),
        ('channel', 'Channel'),
    ]

    type = models.CharField(max_length=10, choices=CONVERSATION_TYPES, default='direct')
    name = models.CharField(max_length=255, blank=True, null=True, help_text="Group/Channel name")
    description = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='conversation_avatars/', blank=True, null=True)

    # Participants (many-to-many through UserConversation for roles and permissions)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='UserConversation',
        related_name='conversations'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_conversations'
    )

    # Settings
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    allow_guests = models.BooleanField(default=False)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['type', '-updated_at']),
            models.Index(fields=['is_active', '-updated_at']),
        ]

    def __str__(self):
        if self.type == 'direct':
            # For direct messages, show participants
            users = self.participants.all()[:2]
            return f"DM: {' & '.join([u.username for u in users])}"
        return self.name or f"{self.get_type_display()} #{self.id}"

    def get_unread_count(self, user):
        """Get unread message count for a user"""
        last_read = UserConversation.objects.filter(
            conversation=self,
            user=user
        ).first()

        if not last_read or not last_read.last_read_at:
            # For first open, unread means messages from others only.
            return self.messages.exclude(author=user).count()

        return self.messages.filter(
            created_at__gt=last_read.last_read_at
        ).exclude(author=user).count()


class UserConversation(models.Model):
    """
    Through model for user-conversation relationship with roles and permissions.
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')

    # Notification settings
    notifications_enabled = models.BooleanField(default=True)
    is_muted = models.BooleanField(default=False)
    muted_until = models.DateTimeField(null=True, blank=True)

    # Status
    is_pinned = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    # Permissions
    can_send_messages = models.BooleanField(default=True)
    can_add_members = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'conversation']
        ordering = ['-is_pinned', '-conversation__updated_at']
        indexes = [
            models.Index(fields=['user', '-is_pinned']),
            models.Index(fields=['conversation', 'role']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.conversation}"

    def mark_as_read(self):
        """Mark conversation as read for this user"""
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at'])


class Message(models.Model):
    """
    Represents a message in a conversation.
    """
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('file', 'File'),
        ('system', 'System'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages'
    )

    # Content
    type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(help_text="Message text content")

    # Reply/Forward
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    forwarded_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='forwards'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Status
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    # Scheduled messages
    scheduled_for = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['is_deleted', '-created_at']),
        ]

    def __str__(self):
        author_name = self.author.username if self.author else "System"
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{author_name}: {preview}"

    def save(self, *args, **kwargs):
        if not self.pk and self.content and '[link_card]' not in self.content:
            self.content = self._try_enrich_links(self.content)
        super().save(*args, **kwargs)

    @staticmethod
    def _try_enrich_links(text):
        """Detect KB article and news URLs, append [link_card] preview data."""
        import re, json as _json
        cleaned = text.strip()

        kb_pattern = re.compile(
            r'(?:https?://[^/\s]+)?/knowledge/article/([-\w]+)/?',
            re.IGNORECASE
        )
        news_pattern = re.compile(
            r'(?:https?://[^/\s]+)?/news/(\d+)/?',
            re.IGNORECASE
        )

        card = None

        kb_match = kb_pattern.search(cleaned)
        if kb_match:
            try:
                from knowledge.models import Article
                article = Article.objects.filter(slug=kb_match.group(1)).first()
                if article:
                    excerpt = re.sub(r'<[^>]+>', '', article.excerpt or article.content or '')
                    preview = excerpt[:150].strip()
                    if len(excerpt) > 150:
                        preview += '...'
                    card = {
                        'title': article.title,
                        'excerpt': preview,
                        'type': article.get_article_type_display(),
                        'url': f'/knowledge/article/{article.slug}/',
                        'source': 'knowledge',
                    }
            except Exception:
                pass

        if not card:
            news_match = news_pattern.search(cleaned)
            if news_match:
                try:
                    from news.models import News
                    news = News.objects.filter(pk=int(news_match.group(1))).first()
                    if news:
                        excerpt = re.sub(r'<[^>]+>', '', news.excerpt or news.content or '')
                        preview = excerpt[:150].strip()
                        if len(excerpt) > 150:
                            preview += '...'
                        card = {
                            'title': news.title,
                            'excerpt': preview,
                            'type': news.category.name if news.category else 'Новость',
                            'url': f'/news/{news.pk}/',
                            'source': 'news',
                        }
                except Exception:
                    pass

        if card:
            payload = _json.dumps(card, ensure_ascii=False)
            return f'{cleaned}\n[link_card]{payload}'
        return text

    def soft_delete(self):
        """Soft delete the message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def edit(self, new_content):
        """Edit the message content"""
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=['content', 'is_edited', 'edited_at'])


class MessageStatus(models.Model):
    """
    Tracks delivery and read status of messages for each user.
    """
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='statuses'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_statuses'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')

    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['message', 'user']
        verbose_name_plural = 'Message statuses'
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.message.id} -> {self.user.username}: {self.status}"

    def mark_delivered(self):
        """Mark message as delivered"""
        if self.status == 'sent':
            self.status = 'delivered'
            self.delivered_at = timezone.now()
            self.save(update_fields=['status', 'delivered_at'])

    def mark_read(self):
        """Mark message as read"""
        if self.status != 'read':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])


class Attachment(models.Model):
    """
    Represents file attachments to messages.
    """
    ATTACHMENT_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('other', 'Other'),
    ]

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments'
    )

    # File info
    file = models.FileField(upload_to='chat_attachments/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=10, choices=ATTACHMENT_TYPES, default='other')
    mime_type = models.CharField(max_length=100)

    # Media-specific fields
    thumbnail = models.ImageField(upload_to='chat_thumbnails/%Y/%m/%d/', blank=True, null=True)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Duration in seconds for audio/video")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        ordering = ['uploaded_at']
        indexes = [
            models.Index(fields=['message', 'file_type']),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.get_file_type_display()})"

    @property
    def file_size_mb(self):
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)


class Reaction(models.Model):
    """
    Represents emoji reactions to messages.
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_reactions'
    )
    emoji = models.CharField(max_length=10, help_text="Unicode emoji")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user', 'emoji']
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['message', 'emoji']),
        ]

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to message {self.message.id}"


class TypingIndicator(models.Model):
    """
    Tracks users currently typing in a conversation.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='typing_in'
    )
    started_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['conversation', 'user']
        indexes = [
            models.Index(fields=['conversation', 'started_at']),
        ]

    def __str__(self):
        return f"{self.user.username} typing in {self.conversation}"

    def is_expired(self, timeout_seconds=5):
        """Check if typing indicator has expired"""
        return (timezone.now() - self.started_at).seconds > timeout_seconds


class OnlineStatus(models.Model):
    """
    Tracks user online/offline status and last seen.
    """
    PRIVACY_CHOICES = [
        ('everyone', 'Everyone'),
        ('contacts', 'Contacts Only'),
        ('nobody', 'Nobody'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='online_status',
        primary_key=True
    )

    # Status
    is_online = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    # Current activity
    current_conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_users'
    )

    # Privacy settings
    show_online_status = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='everyone'
    )
    show_last_seen = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='everyone'
    )

    # Connection info
    connection_count = models.PositiveIntegerField(default=0, help_text="Number of active connections")

    class Meta:
        verbose_name_plural = 'Online statuses'
        indexes = [
            models.Index(fields=['is_online', 'last_activity_at']),
        ]

    def __str__(self):
        status = "Online" if self.is_online else "Offline"
        return f"{self.user.username}: {status}"

    def go_online(self):
        """Mark user as online"""
        self.is_online = True
        self.connection_count += 1
        self.save(update_fields=['is_online', 'connection_count', 'last_activity_at'])

    def go_offline(self):
        """Mark user as offline"""
        self.connection_count = max(0, self.connection_count - 1)
        if self.connection_count == 0:
            self.is_online = False
            self.last_seen_at = timezone.now()
        self.save(update_fields=['is_online', 'connection_count', 'last_seen_at', 'last_activity_at'])

    def update_activity(self, conversation=None):
        """Update last activity timestamp"""
        self.last_activity_at = timezone.now()
        if conversation:
            self.current_conversation = conversation
        self.save(update_fields=['last_activity_at', 'current_conversation'])

    def touch_activity(self, conversation=None):
        """Пинг активности без увеличения счётчика соединений (heartbeat)."""
        self.update_activity(conversation=conversation)
