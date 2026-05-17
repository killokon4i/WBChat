"""
Сервис для работы с @упоминаниями в комментариях.
"""
import re
from typing import List
from django.contrib.auth import get_user_model

User = get_user_model()


class MentionService:
    """
    Сервис обработки @упоминаний:
    - Извлечение @username из текста
    - Отправка уведомлений упомянутым
    - Подсветка упоминаний в HTML
    """

    MENTION_PATTERN = re.compile(r'@(\w+)')

    def extract_mentions(self, text: str) -> List:
        """
        Извлечь упоминания из текста.
        
        Args:
            text: Текст комментария
            
        Returns:
            QuerySet пользователей, упомянутых в тексте
        """
        usernames = self.MENTION_PATTERN.findall(text)
        if not usernames:
            return User.objects.none()
        
        return User.objects.filter(
            username__in=usernames,
            is_active=True,
            is_archived=False
        )

    def notify_mentioned(self, comment, mentioned_users) -> int:
        """
        Отправить уведомления упомянутым пользователям.
        
        Args:
            comment: NewsComment объект
            mentioned_users: QuerySet пользователей
            
        Returns:
            Количество отправленных уведомлений
        """
        from notifications.models import Notification, NotificationType
        
        # Получаем тип уведомления
        notification_type, _ = NotificationType.objects.get_or_create(
            code='mention',
            defaults={
                'name': 'Упоминание',
                'title_template': '{author} упомянул вас в комментарии',
                'body_template': '{content}',
                'priority': 'normal',
            }
        )
        
        count = 0
        for user in mentioned_users:
            # Не уведомляем автора комментария
            if user == comment.author:
                continue
            
            Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=f'{comment.author.get_full_name()} упомянул вас в комментарии',
                content=comment.content[:200],
                link=f'/news/{comment.news.id}/#comment-{comment.id}'
            )
            count += 1
        
        return count

    def highlight_mentions(self, text: str) -> str:
        """
        Заменить @username на HTML ссылки.
        
        Args:
            text: Исходный текст
            
        Returns:
            Текст с HTML ссылками на профили
        """
        def replace_mention(match):
            username = match.group(1)
            user = User.objects.filter(username=username, is_active=True).first()
            if user:
                return f'<a href="/directory/employee/{user.id}/" class="mention">@{username}</a>'
            return f'@{username}'
        
        return self.MENTION_PATTERN.sub(replace_mention, text)

    def process_comment(self, comment) -> List:
        """
        Полная обработка комментария: извлечение упоминаний и уведомления.
        
        Args:
            comment: NewsComment объект
            
        Returns:
            Список упомянутых пользователей
        """
        mentioned_users = list(self.extract_mentions(comment.content))
        
        # Сохраняем связи
        comment.mentions.set(mentioned_users)
        
        # Отправляем уведомления
        self.notify_mentioned(comment, mentioned_users)
        
        return mentioned_users


